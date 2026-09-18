using CSV, DataFrames, Statistics, Optim, Distributions, Plots, Random

# =============================================================================
# CONFIG — flip these flags, then run:
#   julia mis_lba_pm_basic.jl
# =============================================================================

subject_id = 28
min_rt_ms = 100.0
n_starts = 1
sv = 1.0   # LBA drift noise; fixed as a scale (same idea as Strickland)

# If true, the PM weight sits in the same MIS sum as the three locations,
# so adding PM automatically slows ongoing drifts (capacity sharing).
# If false, location drifts ignore PM, and PM has its own drift.
share_pm_capacity = true

# C is MIS total capacity. Strickland has no C; MIS uses one shared C.
# true -> separate C_ongoing and C_pm (and/or by phase if that flag is on).
vary_C_by_accumulator = false
vary_C_by_phase = false          # baseline / focal / nonfocal

# k is the LBA threshold gap: b = A + k.
# Strickland lets threshold differ for ongoing vs PM. Default follows that.
vary_k_by_accumulator = true
vary_k_by_phase = false

# =============================================================================
# Small helpers used below
# =============================================================================

flag_on(x) = lowercase(strip(string(x))) in ("1", "1.0", "true", "t", "yes", "y")

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

push!(param_names, "omega_pm_absent")
push!(lower, 1e-6); push!(upper, 50.0); push!(x0, 0.05)

push!(param_names, "omega_pm_present")
push!(lower, 1e-6); push!(upper, 50.0); push!(x0, 2.0)

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

function trial_omega_pm(x, pm_trial)
    return pm_trial ? x[4] : x[3]
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
        omega_pm = trial_omega_pm(x, is_pm_trial[i])
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
omega_pm_absent_hat = best[3]
omega_pm_present_hat = best[4]
A_hat = best[idx_A]
t0_hat = best[idx_t0]

println()
println("Trials used: ", nrow(data))
println("share_pm_capacity: ", share_pm_capacity)
println("vary_C_by_accumulator: ", vary_C_by_accumulator, "  vary_C_by_phase: ", vary_C_by_phase)
println("vary_k_by_accumulator: ", vary_k_by_accumulator, "  vary_k_by_phase: ", vary_k_by_phase)
for (name, val) in zip(param_names, best)
    println(name, "_hat: ", round(val; digits=6))
end
println("NLL: ", round(best_nll; digits=2))

# =============================================================================
# Simple predicted vs data plot (MIS choice probabilities, no RT integral)
# =============================================================================

function mis_probs(rewards, theta, omega0, omega_pm, share_pm, n_acc, r_max)
    w = [rv == 0 ? omega0 : exp(theta * rv / r_max) for rv in rewards]
    if n_acc == 3
        return w ./ sum(w)
    end
    if share_pm
        w_all = [w[1], w[2], w[3], omega_pm]
        return w_all ./ sum(w_all)
    else
        p = w ./ sum(w)
        p_pm = omega_pm / (omega_pm + 1.0)
        return [(1 - p_pm) * p[1], (1 - p_pm) * p[2], (1 - p_pm) * p[3], p_pm]
    end
end

phase_order = [:baseline, :focal, :nonfocal]
phase_label = Dict(:baseline => "Baseline", :focal => "Focal PM", :nonfocal => "Nonfocal PM")

pred_best = Float64[]
data_best = Float64[]
pred_pmhit = Float64[]
data_pmhit = Float64[]
plot_names = String[]

for ph in phase_order
    idx = findall(i -> phase[i] == ph && !is_pm_trial[i] && choice[i] != 4, 1:nrow(data))
    isempty(idx) && continue
    pred = Float64[]
    obs = Float64[]
    for i in idx
        n_acc = is_pm_phase[i] ? 4 : 3
        omega_pm = is_pm_trial[i] ? omega_pm_present_hat : omega_pm_absent_hat
        p = mis_probs(trial_rewards[i], theta_hat, omega0_hat, omega_pm, share_pm_capacity, n_acc, r_max)
        best_r = maximum(trial_rewards[i])
        best_locs = findall(==(best_r), trial_rewards[i])
        push!(pred, sum(p[j] for j in best_locs))
        push!(obs, choice[i] in best_locs ? 1.0 : 0.0)
    end
    push!(plot_names, phase_label[ph])
    push!(pred_best, mean(pred))
    push!(data_best, mean(obs))
    println(phase_label[ph], " ongoing n=", length(idx),
            " P(best) pred=", round(mean(pred); digits=3),
            " data=", round(mean(obs); digits=3))
end

pm_names = String[]
for ph in [:focal, :nonfocal]
    idx = findall(i -> phase[i] == ph && is_pm_trial[i], 1:nrow(data))
    isempty(idx) && continue
    pred = Float64[]
    obs = Float64[]
    for i in idx
        p = mis_probs(trial_rewards[i], theta_hat, omega0_hat, omega_pm_present_hat, share_pm_capacity, 4, r_max)
        push!(pred, p[4])
        push!(obs, choice[i] == 4 ? 1.0 : 0.0)
    end
    push!(pm_names, phase_label[ph])
    push!(pred_pmhit, mean(pred))
    push!(data_pmhit, mean(obs))
    println(phase_label[ph], " PM n=", length(idx),
            " hit pred=", round(mean(pred); digits=3),
            " data=", round(mean(obs); digits=3))
end

p_acc = plot(
    1:length(plot_names), pred_best;
    label="Prediction", marker=:circle, lw=2, color=:blue,
    ylim=(0, 1.05), xticks=(1:length(plot_names), plot_names),
    ylabel="P(highest reward)", title="Ongoing choice (non-PM trials)",
    legend=:bottomright,
)
plot!(p_acc, 1:length(plot_names), data_best; label="Data", marker=:diamond, lw=2, color=:red)

p_pm = plot(
    1:length(pm_names), pred_pmhit;
    label="Prediction", marker=:circle, lw=2, color=:blue,
    ylim=(0, 1.05), xticks=(1:length(pm_names), pm_names),
    ylabel="PM hit rate", title="PM trials",
    legend=:bottomright,
)
plot!(p_pm, 1:length(pm_names), data_pmhit; label="Data", marker=:diamond, lw=2, color=:red)

fig = plot(p_acc, p_pm; layout=(1, 2), size=(900, 400))
fig_dir = joinpath(@__DIR__, "figs")
isdir(fig_dir) || mkdir(fig_dir)
fig_path = joinpath(fig_dir, "mis_lba_pm_basic_sub$(subject_id).png")
savefig(fig, fig_path)
println("Saved plot: ", fig_path)
