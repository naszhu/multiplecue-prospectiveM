# Practice-adjusted PM monitoring cost.
# Compares naive cost (all PM − all baseline) vs late-baseline − early-PM.
#
#   Rscript analysis/pm_cost_practice_adjusted.R

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
})

exclude_subject_ids <- c(100L)
rt_max_ms <- 4000
exclude_warmup <- TRUE
exclude_burnin <- TRUE
exclude_timeouts <- TRUE

phase_map <- c(
  baseline = "Baseline",
  focal_pm = "Focal PM",
  nonfocal_pm = "Nonfocal PM"
)
pm_phase_levels <- c("Focal PM", "Nonfocal PM")
phase_colors <- c("Focal PM" = "#F58518", "Nonfocal PM" = "#54A24B")

find_project_root <- function() {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", cmd_args, value = TRUE)
  if (length(file_arg)) {
    script_dir <- dirname(normalizePath(sub("^--file=", "", file_arg), winslash = "/"))
    if (basename(script_dir) == "analysis") {
      return(normalizePath(file.path(script_dir, ".."), winslash = "/"))
    }
    return(script_dir)
  }
  if (dir.exists(file.path("exp", "data_from_lab"))) return(normalizePath(".", winslash = "/"))
  if (dir.exists(file.path("..", "exp", "data_from_lab"))) return(normalizePath("..", winslash = "/"))
  stop("Cannot find exp/data_from_lab.")
}

is_true_flag <- function(x) {
  tolower(trimws(as.character(x))) %in% c("1", "true", "t", "yes", "y")
}

is_timeout_response <- function(response) {
  r <- tolower(trimws(as.character(response)))
  is.na(r) | r == "" | r %in% c("timeout", "none")
}

discover_subject_ids <- function(data_dir, exclude_ids = integer(0)) {
  sub_dirs <- list.dirs(data_dir, full.names = FALSE, recursive = FALSE)
  sub_dirs <- sub_dirs[grepl("^sub\\d+$", sub_dirs)]
  ids <- sort(unique(as.integer(sub("^sub", "", sub_dirs))))
  ids <- ids[!ids %in% exclude_ids]
  ids[vapply(ids, function(sid) {
    length(list.files(
      file.path(data_dir, paste0("sub", sid)),
      pattern = paste0("^PMCP_subj", sid, "_ses\\d+.*_trials.*\\.csv$"),
      ignore.case = TRUE
    )) > 0
  }, logical(1))]
}

read_subject_trials <- function(data_dir, subject_id) {
  sub_dir <- file.path(data_dir, paste0("sub", subject_id))
  pat <- paste0("^PMCP_subj", subject_id, "_ses(\\d+).*?_trials.*?\\.csv$")
  paths <- list.files(sub_dir, pattern = pat, full.names = TRUE, ignore.case = TRUE)
  if (!length(paths)) return(NULL)

  file_df <- data.frame(
    path = paths,
    session = as.integer(sub(pat, "\\1", basename(paths))),
    size = file.info(paths)$size,
    stringsAsFactors = FALSE
  ) %>%
    group_by(session) %>%
    slice_max(order_by = size, n = 1, with_ties = FALSE) %>%
    ungroup()

  needed <- c(
    "Session", "WarmUpTrial", "BurnInBlock", "PMPracticeBlock",
    "Response", "RT", "SessionPhase", "PMTrial"
  )
  bind_rows(lapply(file_df$path, function(path) {
    df <- read.csv(path, stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
    for (col in needed) if (!(col %in% names(df))) df[[col]] <- NA_character_
    df
  }))
}

prepare_ongoing <- function(raw_df) {
  raw_df %>%
    mutate(
      SessionNumInt = suppressWarnings(as.integer(Session)),
      PhaseRaw = tolower(trimws(SessionPhase)),
      Phase = unname(phase_map[PhaseRaw]),
      RT_ms = suppressWarnings(as.numeric(RT)),
      WarmUpFlag = is_true_flag(WarmUpTrial),
      BurnInFlag = is_true_flag(BurnInBlock),
      PMPracticeFlag = is_true_flag(PMPracticeBlock),
      TimeoutFlag = is_timeout_response(Response),
      PMTrialFlag = is_true_flag(PMTrial)
    ) %>%
    filter(PhaseRaw %in% names(phase_map), !PMTrialFlag) %>%
    { if (exclude_warmup) filter(., !WarmUpFlag) else . } %>%
    { if (exclude_burnin) filter(., !BurnInFlag) else . } %>%
    filter(!PMPracticeFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    filter(!is.na(RT_ms), RT_ms >= 0, RT_ms <= rt_max_ms, !is.na(SessionNumInt))
}

half_sessions <- function(sessions, which = c("early", "late")) {
  which <- match.arg(which)
  sessions <- sort(unique(sessions))
  if (!length(sessions)) return(integer(0))
  if (length(sessions) == 1) return(sessions)
  cut <- ceiling(length(sessions) / 2)
  if (which == "early") sessions[seq_len(cut)] else sessions[(cut + 1):length(sessions)]
}

cost_for_subject <- function(df, subject_id) {
  base_ses <- sort(unique(df$SessionNumInt[df$Phase == "Baseline"]))
  if (!length(base_ses)) return(NULL)

  early_b_ses <- half_sessions(base_ses, "early")
  late_b_ses <- half_sessions(base_ses, "late")

  med <- function(phase, sessions = NULL) {
    x <- df %>% filter(Phase == phase)
    if (!is.null(sessions)) x <- x %>% filter(SessionNumInt %in% sessions)
    if (!nrow(x)) return(NA_real_)
    median(x$RT_ms)
  }

  out <- list()
  for (ph in pm_phase_levels) {
    pm_ses <- sort(unique(df$SessionNumInt[df$Phase == ph]))
    if (!length(pm_ses)) next
    early_pm_ses <- half_sessions(pm_ses, "early")
    late_pm_ses <- half_sessions(pm_ses, "late")

    out[[ph]] <- tibble(
      SubjectId = subject_id,
      Phase = ph,
      naive_cost = med(ph) - med("Baseline"),
      lateB_earlyPM = med(ph, early_pm_ses) - med("Baseline", late_b_ses),
      lateB_latePM = med(ph, late_pm_ses) - med("Baseline", late_b_ses),
      earlyB_earlyPM = med(ph, early_pm_ses) - med("Baseline", early_b_ses),
      early_baseline = med("Baseline", early_b_ses),
      late_baseline = med("Baseline", late_b_ses),
      early_pm = med(ph, early_pm_ses),
      late_pm = med(ph, late_pm_ses),
      n_base_sessions = length(base_ses),
      n_pm_sessions = length(pm_ses)
    )
  }
  if (!length(out)) return(NULL)
  bind_rows(out)
}

proj_root <- find_project_root()
data_dir <- file.path(proj_root, "exp", "data_from_lab")
fig_root <- file.path(proj_root, "analysis", "fig")
dir.create(fig_root, recursive = TRUE, showWarnings = FALSE)

cli_subjects <- suppressWarnings(as.integer(commandArgs(trailingOnly = TRUE)))
cli_subjects <- cli_subjects[!is.na(cli_subjects)]
subject_ids <- if (length(cli_subjects)) sort(unique(cli_subjects)) else {
  discover_subject_ids(data_dir, exclude_subject_ids)
}

message("Practice-adjusted costs for: ", paste(subject_ids, collapse = ", "))

cost_list <- list()
traj_list <- list()
for (sid in subject_ids) {
  raw <- read_subject_trials(data_dir, sid)
  if (is.null(raw)) next
  df <- prepare_ongoing(raw)
  if (!nrow(df)) next

  traj_list[[as.character(sid)]] <- df %>%
    group_by(SessionNumInt, Phase) %>%
    summarize(median_rt = median(RT_ms), n = n(), .groups = "drop") %>%
    mutate(SubjectId = sid)

  cs <- cost_for_subject(df, sid)
  if (!is.null(cs)) cost_list[[as.character(sid)]] <- cs
}

cost_df <- bind_rows(cost_list)
traj_df <- bind_rows(traj_list)
if (!nrow(cost_df)) stop("No costs computed.")

write.csv(cost_df, file.path(fig_root, "pm_cost_practice_adjusted.csv"), row.names = FALSE)

long_df <- cost_df %>%
  select(SubjectId, Phase, naive_cost, lateB_earlyPM) %>%
  pivot_longer(
    cols = c(naive_cost, lateB_earlyPM),
    names_to = "Estimator",
    values_to = "cost_ms"
  ) %>%
  mutate(
    Estimator = recode(
      Estimator,
      naive_cost = "Naive: all PM − all baseline",
      lateB_earlyPM = "Adjusted: early PM − late baseline"
    ),
    Phase = factor(Phase, levels = pm_phase_levels),
    SubjectLabel = paste0("S", SubjectId)
  )

p_compare <- ggplot(long_df, aes(x = SubjectLabel, y = cost_ms, fill = Phase)) +
  geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
  geom_col(position = position_dodge(width = 0.8), width = 0.72, alpha = 0.92) +
  facet_wrap(~Estimator, ncol = 1) +
  scale_fill_manual(values = phase_colors, drop = FALSE) +
  labs(
    title = "Monitoring cost: naive vs practice-adjusted",
    subtitle = "Adjusted uses second-half baseline sessions vs first-half PM sessions (ongoing non-PM trials).",
    x = NULL,
    y = "Cost (ms)",
    fill = "Phase"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    strip.text = element_text(face = "bold"),
    legend.position = "bottom"
  )

ggsave(
  file.path(fig_root, "pm_cost_naive_vs_practice_adjusted.png"),
  p_compare,
  width = max(10, 0.65 * n_distinct(long_df$SubjectId) + 4),
  height = 8,
  dpi = 300,
  bg = "white"
)

# Session trajectories for reverse-cost subjects of interest
focus_ids <- cost_df %>%
  filter(naive_cost < 0) %>%
  pull(SubjectId) %>%
  unique()
if (!length(focus_ids)) focus_ids <- subject_ids

p_traj <- traj_df %>%
  filter(SubjectId %in% focus_ids) %>%
  mutate(
    Phase = factor(Phase, levels = c("Baseline", "Focal PM", "Nonfocal PM")),
    SubjectLabel = paste0("Subject ", SubjectId)
  ) %>%
  ggplot(aes(x = SessionNumInt, y = median_rt, color = Phase, group = Phase)) +
  geom_line(linewidth = 0.9) +
  geom_point(size = 2) +
  facet_wrap(~SubjectLabel, scales = "free_y") +
  scale_color_manual(
    values = c("Baseline" = "#4C78A8", "Focal PM" = "#F58518", "Nonfocal PM" = "#54A24B"),
    drop = FALSE
  ) +
  labs(
    title = "Ongoing-task median RT by session (subjects with naive cost < 0)",
    subtitle = "Downward baseline slopes = practice before PM starts.",
    x = "Session",
    y = "Median RT (ms)",
    color = "Phase"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold"),
    legend.position = "bottom",
    strip.text = element_text(face = "bold")
  )

ggsave(
  file.path(fig_root, "pm_rt_session_trajectory_reverse_cost.png"),
  p_traj,
  width = 11,
  height = max(5, 2.8 * ceiling(length(focus_ids) / 3)),
  dpi = 300,
  bg = "white"
)

# Console summary
neg <- cost_df %>% filter(naive_cost < 0)
rescued <- neg %>% filter(lateB_earlyPM > 0)
still_neg <- neg %>% filter(lateB_earlyPM <= 0)

cat(
  "Naive mean cost: ", sprintf("%+.1f", mean(cost_df$naive_cost, na.rm = TRUE)), " ms\n",
  "Adjusted (lateB−earlyPM) mean: ", sprintf("%+.1f", mean(cost_df$lateB_earlyPM, na.rm = TRUE)), " ms\n",
  "Negative naive cells: ", nrow(neg),
  "; flipped positive after adjust: ", nrow(rescued),
  "; still ≤0: ", nrow(still_neg), "\n",
  sep = ""
)
if (nrow(rescued)) {
  cat("Rescued: ", paste(sprintf("S%s %s", rescued$SubjectId, rescued$Phase), collapse = "; "), "\n", sep = "")
}
if (nrow(still_neg)) {
  cat("Still ≤0: ", paste(sprintf("S%s %s (%+.0f)", still_neg$SubjectId, still_neg$Phase, still_neg$lateB_earlyPM), collapse = "; "), "\n", sep = "")
}
cat("Saved plots + csv under analysis/fig/\n")
