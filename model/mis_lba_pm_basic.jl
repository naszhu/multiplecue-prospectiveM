using CSV, DataFrames, Statistics, Optim, Distributions, Plots, Random

# =============================================================================
# CONFIG — flip these flags, then run:
#   julia mis_lba_pm_basic.jl
# =============================================================================

subject_id = 28
min_rt_ms = 100.0
n_starts = 1
n_pred_sims = 50   # simulated datasets for prediction means + 95% interval
sv = 1.0   # LBA drift noise; fixed as a scale (same idea as Strickland)

# If true, the PM weight sits in the same MIS sum as the three locations,
# so adding PM automatically slows ongoing drifts (capacity sharing).
# If false, location drifts ignore PM, and PM has its own drift.
share_pm_capacity = true

# C is MIS total capacity. Strickland has no C (he lets mean drift v change
# by PM block instead). Keep C shared unless you want a MIS-style capacity shift.
vary_C_by_accumulator = false
vary_C_by_phase = false          # baseline / focal / nonfocal

# k is the LBA threshold gap: b = A + k.
# Strickland: B varies by accumulator AND by PM block (control / focal / nonfocal).
vary_k_by_accumulator = true
vary_k_by_phase = true

# Strickland: PM mean drift v_PM differs for focal vs nonfocal, and for
# PM-present vs PM-absent trials. That is these two PM weights.
vary_pm_weight_by_phase = true

# =============================================================================
# Small helpers used below
# =============================================================================

flag_on(x) = lowercase(strip(string(x))) in ("1", "1.0", "true", "t", "yes", "y")

function cue_label(x)
    s = strip(replace(string(x), "\"" => ""))
    return startswith(s, "(") ? s : "(" * s * ")"
end

function is_timeout(response)
    s = lowercase(strip(string(response)))
    return s == "" || s == "timeout" || s == "none"
end

function phase_sym(phase_text)
    s = lowercase(strip(string(phase_text)))
    s == "baseline" && return :baseline
    s == "focal_pm" && return :focal
    s == "nonfocal_pm" && return :nonfocal
    return :other
end

# Names for C and k. Accumulators are grouped as ongoing (locations 1-3) vs pm.
function param_keys(vary_acc, vary_phase)
    if vary_acc && vary_phase
        return [:ongoing_baseline, :ongoing_focal, :ongoing_nonfocal, :pm_focal, :pm_nonfocal]
    elseif vary_acc
        return [:ongoing, :pm]
    elseif vary_phase
        return [:baseline, :focal, :nonfocal]
    else
        return [:all]
    end
end

function lookup_key(vary_acc, vary_phase, acc, phase)
    if vary_acc && vary_phase
        return Symbol(string(acc), "_", string(phase))
    elseif vary_acc
        return acc
    elseif vary_phase
        return phase
    else
        return :all
    end
end

function scope_tag(vary_acc, vary_phase, name)
    vary_acc && vary_phase && return "$(name)-acc-phase"
    vary_acc && return "$(name)-acc"
    vary_phase && return "$(name)-phase"
    return "$(name)-shared"
end

# Filename tag like RTfit: sharePM__C-shared__k-acc-phase__wPM-phase
function model_tag()
    pm_part = share_pm_capacity ? "sharePM" : "indepPM"
    w_part = vary_pm_weight_by_phase ? "wPM-phase" : "wPM-shared"
    return join([
        pm_part,
        scope_tag(vary_C_by_accumulator, vary_C_by_phase, "C"),
        scope_tag(vary_k_by_accumulator, vary_k_by_phase, "k"),
        w_part,
    ], "__")
end

function wrap_join(items; sep="   ", width=140)
    lines = String[]
    cur = ""
    for item in items
        trial = isempty(cur) ? item : cur * sep * item
        if length(trial) > width && !isempty(cur)
            push!(lines, cur)
            cur = item
        else
            cur = trial
        end
    end
    isempty(cur) || push!(lines, cur)
    return join(lines, "\n")
end

function text_banner(title_text)
    p = plot(
        xlims=(0, 1), ylims=(0, 1);
        axis=false, grid=false, legend=false, ticks=false, framestyle=:none,
    )
    annotate!(p, 0.0, 0.55, text(title_text, :left, 9))
    return p
end

# =============================================================================
# Custom LBA race (Brown & Heathcote, 2008)
# Each accumulator can have its own threshold gap k.
# SequentialSamplingModels cannot do that, because its k is a single number.
# =============================================================================

const UNIT_NORMAL = Normal(0.0, 1.0)
phi(x) = pdf(UNIT_NORMAL, x)
Phi(x) = cdf(UNIT_NORMAL, x)

# Density of one accumulator finishing at decision time t = RT - t0.
function lba_one_pdf(t, v, A, b, s)
    t <= 0 && return 0.0
    n1 = (b - A - t * v) / (t * s)
    n2 = (b - t * v) / (t * s)
    dens = (1 / A) * (-v * Phi(n1) + s * phi(n1) + v * Phi(n2) - s * phi(n2))
    return max(dens, 0.0)
end

# CDF of one accumulator finishing before decision time t.
function lba_one_cdf(t, v, A, b, s)
    t <= 0 && return 0.0
    n1 = (b - A - t * v) / (t * s)
    n2 = (b - t * v) / (t * s)
    return 1 + ((b - A - t * v) / A) * Phi(n1) - ((b - t * v) / A) * Phi(n2) +
        ((t * s) / A) * phi(n1) - ((t * s) / A) * phi(n2)
end

# Joint density that accumulator `choice` wins at time `rt`.
# k_vec[i] is the threshold gap for accumulator i. b_i = A + k_vec[i].
function lba_race_pdf(rt, choice, v, A, k_vec, t0, s)
    dt = rt - t0
    (dt <= 0 || A <= 0) && return 0.0
    lik = 1.0
    for i in eachindex(v)
        b = A + k_vec[i]
        if i == choice
            lik *= lba_one_pdf(dt, v[i], A, b, s)
        else
            lik *= max(0.0, 1 - lba_one_cdf(dt, v[i], A, b, s))
        end
    end
    # Chance that every drift is negative (nobody finishes). Divide it out.
    pneg = 1.0
    for i in eachindex(v)
        pneg *= Phi(-v[i] / s)
    end
    return max(lik / max(1 - pneg, 1e-12), 0.0)
end

# Draw one LBA race. Used for RT/accuracy prediction plots, not for fitting.
function lba_simulate(rng, v, A, k_vec, t0, s)
    n = length(v)
    drifts = Vector{Float64}(undef, n)
    while true
        for i in 1:n
            drifts[i] = v[i] + s * randn(rng)
        end
        any(>(0), drifts) && break
    end
    start = A .* rand(rng, n)
    best_i = 1
    best_t = Inf
    for i in 1:n
        drifts[i] <= 0 && continue
        t = (A + k_vec[i] - start[i]) / drifts[i]
        if t < best_t
            best_t = t
            best_i = i
        end
    end
    return best_i, t0 + best_t
end

# MIS weights for the three locations, then optional PM weight.
# v_i = C_i * w_i / sum(w)
function trial_drifts(rewards, theta, omega0, omega_pm, C_vec, share_pm, r_max)
    w = [rv == 0 ? omega0 : exp(theta * rv / r_max) for rv in rewards]
    n_acc = length(C_vec)
    if n_acc == 3
        p = w ./ sum(w)
        return C_vec .* p
    end
    if share_pm
        w_all = [w[1], w[2], w[3], omega_pm]
        p = w_all ./ sum(w_all)
        return C_vec .* p
    else
        p = w ./ sum(w)
        v_pm = C_vec[4] * omega_pm / (omega_pm + 1.0)
        return [C_vec[1] * p[1], C_vec[2] * p[2], C_vec[3] * p[3], v_pm]
    end
end

function trial_k_vec(k_ongoing, k_pm, n_acc)
    n_acc == 3 && return [k_ongoing, k_ongoing, k_ongoing]
    return [k_ongoing, k_ongoing, k_ongoing, k_pm]
end

function trial_C_vec(C_ongoing, C_pm, n_acc)
    n_acc == 3 && return [C_ongoing, C_ongoing, C_ongoing]
    return [C_ongoing, C_ongoing, C_ongoing, C_pm]
end

# =============================================================================
# Load subject 28 formal trials
# =============================================================================

data_dir = joinpath(@__DIR__, "..", "exp", "data_from_lab", "sub$(subject_id)")
all_csv = filter(f -> endswith(f, ".csv"), readdir(data_dir; join=true))
trial_files = filter(f -> occursin(r"_ses\d+.*_trials.*\.csv$", basename(f)), all_csv)
@assert !isempty(trial_files) "No trial CSVs in $(data_dir)"

# If a session was re-run, several files share the same session number.
# Keep the largest file, same rule as the R analysis scripts.
best_file = Dict{Int, String}()
best_size = Dict{Int, Int}()
for f in trial_files
    m = match(r"_ses(\d+)", basename(f))
    m === nothing && continue
    ses = parse(Int, m.captures[1])
    sz = filesize(f)
    if !haskey(best_file, ses) || sz > best_size[ses]
        best_file[ses] = f
        best_size[ses] = sz
    end
end
chosen_files = [best_file[ses] for ses in sort(collect(keys(best_file)))]
println("Subject ", subject_id, " session files: ", length(chosen_files))

col_types = Dict(
    :CueValues => String,
    :Response => String,
    :SessionPhase => String,
    :PMKey => String,
    :RespLoc => String,
    :PMResponse => String,
    :PMTrial => String,
    :WarmUpTrial => String,
    :BurnInBlock => String,
    :PMPracticeBlock => String,
)

frames = DataFrame[]
for f in chosen_files
    push!(frames, CSV.read(f, DataFrame; types=col_types))
end
raw = vcat(frames...; cols=:union)

formal_phases = Set(["baseline", "focal_pm", "nonfocal_pm"])
keep = trues(nrow(raw))
for i in 1:nrow(raw)
    phase = lowercase(strip(string(raw.SessionPhase[i])))
    if !(phase in formal_phases)
        keep[i] = false
        continue
    end
    if flag_on(raw.WarmUpTrial[i]) || flag_on(raw.BurnInBlock[i]) || flag_on(raw.PMPracticeBlock[i])
        keep[i] = false
        continue
    end
    if is_timeout(raw.Response[i])
        keep[i] = false
        continue
    end
    rt = tryparse(Float64, string(raw.RT[i]))
    if rt === nothing || rt < min_rt_ms
        keep[i] = false
        continue
    end
    cue_values = string(raw.CueValues[i])
    if length(cue_values) != 3 || !all(isdigit, cue_values)
        keep[i] = false
        continue
    end
    pm_key = lowercase(strip(string(raw.PMKey[i])))
    response = lowercase(strip(string(raw.Response[i])))
    pm_resp = flag_on(raw.PMResponse[i]) || response == pm_key
    is_pm_phase = phase != "baseline"
    if pm_resp
        # Baseline has no PM accumulator, so drop baseline PM-key presses
        # (same idea as Strickland dropping control-block PM responses).
        if !is_pm_phase
            keep[i] = false
        end
        continue
    end
    loc = tryparse(Int, string(raw.RespLoc[i]))
    if loc === nothing || !(loc in 1:3)
        keep[i] = false
    end
end
data = raw[keep, :]
@assert nrow(data) > 0 "No formal trials left after filtering."

trial_rewards = [parse.(Int, collect(string(v))) for v in data.CueValues]
rt_sec = [parse(Float64, string(x)) / 1000 for x in data.RT]
phase = [phase_sym(p) for p in data.SessionPhase]
is_pm_phase = [ph != :baseline for ph in phase]
is_pm_trial = [flag_on(x) for x in data.PMTrial]
choice = Vector{Int}(undef, nrow(data))
for i in 1:nrow(data)
    pm_key = lowercase(strip(string(data.PMKey[i])))
    response = lowercase(strip(string(data.Response[i])))
    if flag_on(data.PMResponse[i]) || response == pm_key
        choice[i] = 4
    else
        choice[i] = parse(Int, string(data.RespLoc[i]))
    end
end

conditions = [cue_label(c) for c in data.CueCondition]
condition_order = ["(1)", "(2)", "(3)", "(1,2)", "(1,3)", "(2,3)"]
present_conditions = [cc for cc in condition_order if cc in Set(conditions)]

r_max = maximum(vcat(trial_rewards...))
t0_upper = minimum(rt_sec) - 0.001
@assert t0_upper > 0.001 "All RTs are too small for a positive t0."
eps_val = 1e-12

println("Formal trials used: ", nrow(data))
println("  baseline:   ", count(==(:baseline), phase))
println("  focal:      ", count(==(:focal), phase))
println("  nonfocal:   ", count(==(:nonfocal), phase))
println("  PM trials:  ", count(is_pm_trial))
println("  PM choices: ", count(==(4), choice))

# =============================================================================
# Free parameters (built from the flags above)
# =============================================================================

param_names = String[]
lower = Float64[]
upper = Float64[]
x0 = Float64[]

push!(param_names, "theta")
push!(lower, 0.0); push!(upper, 30.0); push!(x0, 1.0)

push!(param_names, "omega0")
push!(lower, 1e-6); push!(upper, 50.0); push!(x0, 0.1)

idx_omega_pm = Dict{Symbol, Int}()
omega_pm_key_list = vary_pm_weight_by_phase ?
    [:absent_focal, :absent_nonfocal, :present_focal, :present_nonfocal] :
    [:absent, :present]
for key in omega_pm_key_list
    push!(param_names, "omega_pm_$(key)")
    push!(lower, 1e-6); push!(upper, 50.0)
    push!(x0, startswith(string(key), "present") ? 2.0 : 0.05)
    idx_omega_pm[key] = length(param_names)
end

idx_C = Dict{Symbol, Int}()
for key in param_keys(vary_C_by_accumulator, vary_C_by_phase)
    push!(param_names, "C_$(key)")
    push!(lower, 0.01); push!(upper, 100.0); push!(x0, 5.0)
    idx_C[key] = length(param_names)
end

push!(param_names, "A")
push!(lower, 0.001); push!(upper, 5.0); push!(x0, 0.3)
idx_A = length(param_names)

idx_k = Dict{Symbol, Int}()
for key in param_keys(vary_k_by_accumulator, vary_k_by_phase)
    push!(param_names, "k_$(key)")
    push!(lower, 0.001); push!(upper, 5.0); push!(x0, 0.3)
    idx_k[key] = length(param_names)
end

push!(param_names, "t0")
push!(lower, 0.001); push!(upper, t0_upper); push!(x0, min(0.2, t0_upper / 2))
idx_t0 = length(param_names)

println("Free parameters: ", param_names)

function C_pair(x, ph)
    C_ong = x[idx_C[lookup_key(vary_C_by_accumulator, vary_C_by_phase, :ongoing, ph)]]
    pm_key = lookup_key(vary_C_by_accumulator, vary_C_by_phase, :pm, ph)
    C_pm = haskey(idx_C, pm_key) ? x[idx_C[pm_key]] : C_ong
    return C_ong, C_pm
end

function k_pair(x, ph)
    k_ong = x[idx_k[lookup_key(vary_k_by_accumulator, vary_k_by_phase, :ongoing, ph)]]
    pm_key = lookup_key(vary_k_by_accumulator, vary_k_by_phase, :pm, ph)
    k_pm = haskey(idx_k, pm_key) ? x[idx_k[pm_key]] : k_ong
    return k_ong, k_pm
end

function trial_omega_pm(x, pm_trial, ph)
    kind = pm_trial ? :present : :absent
    key = vary_pm_weight_by_phase ? Symbol(kind, "_", ph) : kind
    return x[idx_omega_pm[key]]
end

function neg_loglik(x)
    theta = x[1]
    omega0 = x[2]
    A = x[idx_A]
    t0 = x[idx_t0]
    nll = 0.0
    for i in eachindex(trial_rewards)
        rt_sec[i] <= t0 && return Inf
        n_acc = is_pm_phase[i] ? 4 : 3
        choice[i] > n_acc && return Inf
        C_ong, C_pm = C_pair(x, phase[i])
        k_ong, k_pm = k_pair(x, phase[i])
        C_vec = trial_C_vec(C_ong, C_pm, n_acc)
        k_vec = trial_k_vec(k_ong, k_pm, n_acc)
        omega_pm = n_acc == 4 ? trial_omega_pm(x, is_pm_trial[i], phase[i]) : 0.0
        v = trial_drifts(trial_rewards[i], theta, omega0, omega_pm, C_vec, share_pm_capacity, r_max)
        lik = lba_race_pdf(rt_sec[i], choice[i], v, A, k_vec, t0, sv)
        nll -= log(max(lik, eps_val))
    end
    return nll
end

# =============================================================================
# Fit
# =============================================================================

println("Starting MLE with ", n_starts, " start(s) ...")
best_fit = nothing
best_nll = Inf
rng = MersenneTwister(20260918)
for start_i in 1:n_starts
    start_x = copy(x0)
    if start_i > 1
        for j in eachindex(start_x)
            start_x[j] = clamp(start_x[j] + 0.1 * randn(rng) * (upper[j] - lower[j]), lower[j], upper[j])
        end
    end
    fit = optimize(neg_loglik, lower, upper, start_x, Fminbox(NelderMead()),
                   Optim.Options(g_tol=1e-4, iterations=20_000, show_trace=false))
    nll = Optim.minimum(fit)
    println("  start ", start_i, " NLL=", round(nll; digits=2), " converged=", Optim.converged(fit))
    if nll < best_nll
        global best_nll = nll
        global best_fit = fit
    end
end

best = Optim.minimizer(best_fit)
theta_hat = best[1]
omega0_hat = best[2]
A_hat = best[idx_A]
t0_hat = best[idx_t0]

println()
println("Trials used: ", nrow(data))
println("share_pm_capacity: ", share_pm_capacity)
println("vary_C_by_accumulator: ", vary_C_by_accumulator, "  vary_C_by_phase: ", vary_C_by_phase)
println("vary_k_by_accumulator: ", vary_k_by_accumulator, "  vary_k_by_phase: ", vary_k_by_phase)
println("vary_pm_weight_by_phase: ", vary_pm_weight_by_phase)
for (name, val) in zip(param_names, best)
    println(name, "_hat: ", round(val; digits=6))
end
println("NLL: ", round(best_nll; digits=2))

# =============================================================================
# Prediction plot: phases (columns) x accuracy/RT quantiles (rows)
# Strickland's figures separate control / focal / nonfocal. Cue conditions
# stay on the x-axis (same style as the RTfit current_best plot).
# Ongoing (non-PM) trials are used for accuracy and RT, so phase differences
# are the PM monitoring cost. PM hit rates are printed in the title.
# =============================================================================

chose_max_reward(ch, rewards) = ch in 1:length(rewards) && rewards[ch] == maximum(rewards)

function trial_lba(i, x)
    n_acc = is_pm_phase[i] ? 4 : 3
    C_ong, C_pm = C_pair(x, phase[i])
    k_ong, k_pm = k_pair(x, phase[i])
    C_vec = trial_C_vec(C_ong, C_pm, n_acc)
    k_vec = trial_k_vec(k_ong, k_pm, n_acc)
    omega_pm = n_acc == 4 ? trial_omega_pm(x, is_pm_trial[i], phase[i]) : 0.0
    v = trial_drifts(trial_rewards[i], x[1], x[2], omega_pm, C_vec, share_pm_capacity, r_max)
    return v, x[idx_A], k_vec, x[idx_t0]
end

phase_order = [:baseline, :focal, :nonfocal]
phase_label = Dict(:baseline => "Baseline", :focal => "Focal PM", :nonfocal => "Nonfocal PM")
n_ph = length(phase_order)
n_cond = length(present_conditions)

# Ongoing-task cells: phase × cue condition, excluding PM-present trials.
ong_idx = Dict{Tuple{Symbol, String}, Vector{Int}}()
for ph in phase_order
    for cc in present_conditions
        ong_idx[(ph, cc)] = findall(i -> phase[i] == ph && conditions[i] == cc && !is_pm_trial[i], 1:nrow(data))
    end
end
pm_idx = Dict(ph => findall(i -> phase[i] == ph && is_pm_trial[i], 1:nrow(data)) for ph in [:focal, :nonfocal])

function cell_acc(idx, ch)
    isempty(idx) && return NaN
    return mean(chose_max_reward(ch[i], trial_rewards[i]) for i in idx)
end

function cell_rtq(idx, rts)
    isempty(idx) && return (NaN, NaN, NaN)
    q = quantile(rts[idx], [0.1, 0.5, 0.9])
    return (q[1], q[2], q[3])
end

data_acc = fill(NaN, n_ph, n_cond)
data_rt10 = fill(NaN, n_ph, n_cond)
data_rt50 = fill(NaN, n_ph, n_cond)
data_rt90 = fill(NaN, n_ph, n_cond)
for (ip, ph) in enumerate(phase_order)
    for (jc, cc) in enumerate(present_conditions)
        idx = ong_idx[(ph, cc)]
        data_acc[ip, jc] = cell_acc(idx, choice)
        q10, q50, q90 = cell_rtq(idx, rt_sec)
        data_rt10[ip, jc] = q10
        data_rt50[ip, jc] = q50
        data_rt90[ip, jc] = q90
        println(phase_label[ph], " ", cc, " n=", length(idx),
                " acc=", round(data_acc[ip, jc]; digits=3),
                " rt=", round(q10; digits=3), "/", round(q50; digits=3), "/", round(q90; digits=3))
    end
end

println("Simulating ", n_pred_sims, " datasets for prediction intervals ...")
rng = MersenneTwister(20260918)
acc_sims = fill(NaN, n_pred_sims, n_ph, n_cond)
rt10_sims = fill(NaN, n_pred_sims, n_ph, n_cond)
rt50_sims = fill(NaN, n_pred_sims, n_ph, n_cond)
rt90_sims = fill(NaN, n_pred_sims, n_ph, n_cond)
pmhit_sims = Dict(ph => zeros(n_pred_sims) for ph in [:focal, :nonfocal])
sim_choice = Vector{Int}(undef, nrow(data))
sim_rt = Vector{Float64}(undef, nrow(data))
for s in 1:n_pred_sims
    for i in eachindex(trial_rewards)
        v, A, k_vec, t0 = trial_lba(i, best)
        sim_choice[i], sim_rt[i] = lba_simulate(rng, v, A, k_vec, t0, sv)
    end
    for (ip, ph) in enumerate(phase_order)
        for (jc, cc) in enumerate(present_conditions)
            idx = ong_idx[(ph, cc)]
            isempty(idx) && continue
            acc_sims[s, ip, jc] = cell_acc(idx, sim_choice)
            q10, q50, q90 = cell_rtq(idx, sim_rt)
            rt10_sims[s, ip, jc] = q10
            rt50_sims[s, ip, jc] = q50
            rt90_sims[s, ip, jc] = q90
        end
    end
    for ph in [:focal, :nonfocal]
        idx = pm_idx[ph]
        pmhit_sims[ph][s] = isempty(idx) ? NaN : mean(sim_choice[i] == 4 for i in idx)
    end
end

function sim_mean_ci(mat)
    n = size(mat, 2)
    mu = fill(NaN, n)
    lo = fill(NaN, n)
    hi = fill(NaN, n)
    for j in 1:n
        v = filter(isfinite, mat[:, j])
        isempty(v) && continue
        mu[j] = mean(v)
        lo[j] = quantile(v, 0.025)
        hi[j] = quantile(v, 0.975)
    end
    return mu, lo, hi
end

pred_acc = Dict{Symbol, Vector{Float64}}()
pred_acc_lo = Dict{Symbol, Vector{Float64}}()
pred_acc_hi = Dict{Symbol, Vector{Float64}}()
pred_rt10 = Dict{Symbol, Vector{Float64}}()
pred_rt10_lo = Dict{Symbol, Vector{Float64}}()
pred_rt10_hi = Dict{Symbol, Vector{Float64}}()
pred_rt50 = Dict{Symbol, Vector{Float64}}()
pred_rt50_lo = Dict{Symbol, Vector{Float64}}()
pred_rt50_hi = Dict{Symbol, Vector{Float64}}()
pred_rt90 = Dict{Symbol, Vector{Float64}}()
pred_rt90_lo = Dict{Symbol, Vector{Float64}}()
pred_rt90_hi = Dict{Symbol, Vector{Float64}}()
for (ip, ph) in enumerate(phase_order)
    pred_acc[ph], pred_acc_lo[ph], pred_acc_hi[ph] = sim_mean_ci(acc_sims[:, ip, :])
    pred_rt10[ph], pred_rt10_lo[ph], pred_rt10_hi[ph] = sim_mean_ci(rt10_sims[:, ip, :])
    pred_rt50[ph], pred_rt50_lo[ph], pred_rt50_hi[ph] = sim_mean_ci(rt50_sims[:, ip, :])
    pred_rt90[ph], pred_rt90_lo[ph], pred_rt90_hi[ph] = sim_mean_ci(rt90_sims[:, ip, :])
end

data_pmhit = Dict{Symbol, Float64}()
pred_pmhit = Dict{Symbol, Float64}()
for ph in [:focal, :nonfocal]
    idx = pm_idx[ph]
    data_pmhit[ph] = isempty(idx) ? NaN : mean(choice[i] == 4 for i in idx)
    pred_pmhit[ph] = mean(pmhit_sims[ph])
    println(phase_label[ph], " PM hit data=", round(data_pmhit[ph]; digits=3),
            " pred=", round(pred_pmhit[ph]; digits=3), " n=", length(idx))
end

x = collect(1:n_cond)
xt = (x, present_conditions)
rt10_lim = extrema(filter(isfinite, vcat(vec(data_rt10), pred_rt10[:baseline], pred_rt10[:focal], pred_rt10[:nonfocal])))
rt50_lim = extrema(filter(isfinite, vcat(vec(data_rt50), pred_rt50[:baseline], pred_rt50[:focal], pred_rt50[:nonfocal])))
rt90_lim = extrema(filter(isfinite, vcat(vec(data_rt90), pred_rt90[:baseline], pred_rt90[:focal], pred_rt90[:nonfocal])))
pad(lim) = (lim[1] - 0.05 * (lim[2] - lim[1]), lim[2] + 0.05 * (lim[2] - lim[1]))

function phase_panel(data_y, pred_y, pred_lo, pred_hi; title="", ylabel="", ylims=:auto, pred_color="#2C7FB8", show_legend=false)
    p = plot(
        x, data_y;
        label="Observed", color=:black, marker=:circle, lw=1.4,
        xticks=xt, xrotation=45, ylabel=ylabel, title=title,
        ylims=ylims, legend=show_legend ? :bottomright : false,
    )
    plot!(
        p, x, pred_y;
        label="Predicted", color=pred_color, marker=:circle, lw=1.4,
        yerror=(pred_y .- pred_lo, pred_hi .- pred_y),
    )
    return p
end

panels = Plots.Plot[]
for (ip, ph) in enumerate(phase_order)
    push!(panels, phase_panel(
        data_acc[ip, :], pred_acc[ph], pred_acc_lo[ph], pred_acc_hi[ph];
        title=phase_label[ph], ylabel=ip == 1 ? "P(max reward)" : "",
        ylims=(0, 1.05), pred_color="#2C7FB8", show_legend=(ip == 1),
    ))
end
for (ip, ph) in enumerate(phase_order)
    push!(panels, phase_panel(
        data_rt10[ip, :], pred_rt10[ph], pred_rt10_lo[ph], pred_rt10_hi[ph];
        title="q10", ylabel=ip == 1 ? "RT (s)" : "",
        ylims=pad(rt10_lim), pred_color="#D95F0E",
    ))
end
for (ip, ph) in enumerate(phase_order)
    push!(panels, phase_panel(
        data_rt50[ip, :], pred_rt50[ph], pred_rt50_lo[ph], pred_rt50_hi[ph];
        title="q50", ylabel=ip == 1 ? "RT (s)" : "",
        ylims=pad(rt50_lim), pred_color="#D95F0E",
    ))
end
for (ip, ph) in enumerate(phase_order)
    push!(panels, phase_panel(
        data_rt90[ip, :], pred_rt90[ph], pred_rt90_lo[ph], pred_rt90_hi[ph];
        title="q90", ylabel=ip == 1 ? "RT (s)" : "",
        ylims=pad(rt90_lim), pred_color="#D95F0E", show_legend=(ip == 3),
    ))
end

flag_items = [
    "share_pm_capacity=$(share_pm_capacity)",
    "vary_C_by_accumulator=$(vary_C_by_accumulator)",
    "vary_C_by_phase=$(vary_C_by_phase)",
    "vary_k_by_accumulator=$(vary_k_by_accumulator)",
    "vary_k_by_phase=$(vary_k_by_phase)",
    "vary_pm_weight_by_phase=$(vary_pm_weight_by_phase)",
]
param_items = ["$(name)=$(round(val; digits=3))" for (name, val) in zip(param_names, best)]
pmhit_line = "PM hit  focal data/pred=$(round(data_pmhit[:focal]; digits=3))/$(round(pred_pmhit[:focal]; digits=3))   nonfocal data/pred=$(round(data_pmhit[:nonfocal]; digits=3))/$(round(pred_pmhit[:nonfocal]; digits=3))"
tag = model_tag()
title_text = "sub$(subject_id)  |  $(tag)  |  NLL=$(round(best_nll; digits=1))  |  $(pmhit_line)\n" *
    wrap_join(flag_items; width=140) * "\n" *
    wrap_join(param_items; width=140)

banner = text_banner(title_text)
fig = plot(
    banner, panels...;
    layout=@layout([a{0.13h}; grid(4, 3)]),
    size=(1800, 1400),
)
fig_dir = joinpath(@__DIR__, "figs")
isdir(fig_dir) || mkdir(fig_dir)
fig_path = joinpath(fig_dir, "sub$(subject_id)_$(tag).png")
savefig(fig, fig_path)
println("Saved plot: ", fig_path)

# Overlay: all 3 phases on the same axes.
# Color = phase. Solid = prediction. Dashed = observed.
phase_color = Dict(:baseline => "#4C78A8", :focal => "#F58518", :nonfocal => "#54A24B")

function overlay_panel(data_mat, pred_dict, pred_lo_dict, pred_hi_dict; title="", ylabel="", ylims=:auto, show_legend=false)
    p = plot(
        xticks=xt, xrotation=45, ylabel=ylabel, title=title,
        ylims=ylims, legend=show_legend ? :outertopright : false,
    )
    for (ip, ph) in enumerate(phase_order)
        c = phase_color[ph]
        plot!(
            p, x, data_mat[ip, :];
            color=c, linestyle=:dash, marker=:circle, lw=2,
            label=show_legend ? "$(phase_label[ph]) obs" : "",
        )
        plot!(
            p, x, pred_dict[ph];
            color=c, linestyle=:solid, marker=:diamond, lw=2,
            yerror=(pred_dict[ph] .- pred_lo_dict[ph], pred_hi_dict[ph] .- pred_dict[ph]),
            label=show_legend ? "$(phase_label[ph]) pred" : "",
        )
    end
    return p
end

p_over_acc = overlay_panel(
    data_acc, pred_acc, pred_acc_lo, pred_acc_hi;
    title="Accuracy", ylabel="P(max reward)", ylims=(0, 1.05), show_legend=true,
)
p_over_q10 = overlay_panel(
    data_rt10, pred_rt10, pred_rt10_lo, pred_rt10_hi;
    title="q10", ylabel="RT (s)", ylims=pad(rt10_lim),
)
p_over_q50 = overlay_panel(
    data_rt50, pred_rt50, pred_rt50_lo, pred_rt50_hi;
    title="q50", ylabel="RT (s)", ylims=pad(rt50_lim),
)
p_over_q90 = overlay_panel(
    data_rt90, pred_rt90, pred_rt90_lo, pred_rt90_hi;
    title="q90", ylabel="RT (s)", ylims=pad(rt90_lim),
)

fig_over = plot(
    text_banner("sub$(subject_id)  |  $(tag)  |  overlay  |  dashed=observed  solid=predicted\n" *
        wrap_join(param_items; width=140)),
    p_over_acc, p_over_q10, p_over_q50, p_over_q90;
    layout=@layout([a{0.16h}; [b{0.42w} [c; d; e]]]),
    size=(1500, 1050),
)
fig_over_path = joinpath(fig_dir, "sub$(subject_id)_$(tag)_overlay.png")
savefig(fig_over, fig_over_path)
println("Saved plot: ", fig_over_path)
