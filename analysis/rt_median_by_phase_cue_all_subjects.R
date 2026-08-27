# RT median and accuracy by phase and cue condition for all PM subjects with trial data.
#
# Phases: baseline, focal_pm, nonfocal_pm (practice excluded)
# Cue conditions: (1), (2), (3), (1,2), (1,3), (2,3)
#
# Run from multiplecue-prospectiveM/ or analysis/:
#   Rscript analysis/rt_median_by_phase_cue_all_subjects.R
#   Rscript analysis/rt_median_by_phase_cue_all_subjects.R 17 28

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
})

# ---- CONFIG ----
exclude_subject_ids <- c(100L)
rt_min_ms <- 0
rt_max_ms <- 4000
exclude_timeouts <- TRUE
exclude_warmup <- TRUE
exclude_burnin <- TRUE
exclude_pm_trials <- TRUE
# ----------------

phase_levels <- c("Baseline", "Focal PM", "Nonfocal PM")
phase_map <- c(
  baseline = "Baseline",
  focal_pm = "Focal PM",
  nonfocal_pm = "Nonfocal PM"
)
cue_levels <- c("(1)", "(2)", "(3)", "(1,2)", "(1,3)", "(2,3)")
phase_colors <- c(
  "Baseline" = "#4C78A8",
  "Focal PM" = "#F58518",
  "Nonfocal PM" = "#54A24B"
)

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
  if (dir.exists(file.path("exp", "data_from_lab"))) {
    return(normalizePath(".", winslash = "/"))
  }
  if (dir.exists(file.path("..", "exp", "data_from_lab"))) {
    return(normalizePath("..", winslash = "/"))
  }
  stop("Cannot find exp/data_from_lab. Run from multiplecue-prospectiveM/ or analysis/.")
}

is_true_flag <- function(x) {
  tolower(trimws(as.character(x))) %in% c("1", "true", "t", "yes", "y")
}

is_timeout_response <- function(response) {
  r <- tolower(trimws(as.character(response)))
  is.na(r) | r == "" | r %in% c("timeout", "none")
}

normalize_cue_condition <- function(x) {
  x <- trimws(as.character(x))
  if (is.na(x) || !nzchar(x)) {
    return(NA_character_)
  }
  if (!grepl("^\\(", x)) {
    x <- paste0("(", x, ")")
  }
  x
}

discover_subject_ids <- function(data_dir, exclude_ids = integer(0)) {
  sub_dirs <- list.dirs(data_dir, full.names = FALSE, recursive = FALSE)
  sub_dirs <- sub_dirs[grepl("^sub\\d+$", sub_dirs)]
  ids <- as.integer(sub("^sub", "", sub_dirs))
  ids <- sort(unique(ids[!ids %in% exclude_ids]))
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
  if (!dir.exists(sub_dir)) {
    return(NULL)
  }

  pat <- paste0("^PMCP_subj", subject_id, "_ses(\\d+).*?_trials.*?\\.csv$")
  paths <- list.files(sub_dir, pattern = pat, full.names = TRUE, ignore.case = TRUE)
  if (!length(paths)) {
    return(NULL)
  }

  file_df <- data.frame(
    path = paths,
    session = as.integer(sub(pat, "\\1", basename(paths))),
    size = file.info(paths)$size,
    stringsAsFactors = FALSE
  )
  file_df <- file_df %>%
    group_by(session) %>%
    slice_max(order_by = size, n = 1, with_ties = FALSE) %>%
    ungroup()

  needed <- c(
    "Subject", "Session", "WarmUpTrial", "BurnInBlock", "Response", "RT", "ACC",
    "CueCondition", "SessionPhase", "PMTrial"
  )

  bind_rows(lapply(file_df$path, function(path) {
    df <- read.csv(path, stringsAsFactors = FALSE, colClasses = "character", check.names = FALSE)
    for (col in needed) {
      if (!(col %in% names(df))) {
        df[[col]] <- NA_character_
      }
    }
    df$source_file <- basename(path)
    df
  }))
}

prepare_trials <- function(raw_df) {
  raw_df %>%
    mutate(
      SessionNumInt = suppressWarnings(as.integer(Session)),
      CueConditionNorm = vapply(CueCondition, normalize_cue_condition, character(1)),
      PhaseRaw = tolower(trimws(SessionPhase)),
      Phase = unname(phase_map[PhaseRaw]),
      RT_ms = suppressWarnings(as.numeric(RT)),
      ACC_num = suppressWarnings(as.numeric(ACC)),
      WarmUpFlag = is_true_flag(WarmUpTrial),
      BurnInFlag = is_true_flag(BurnInBlock),
      TimeoutFlag = is_timeout_response(Response),
      PMTrialFlag = is_true_flag(PMTrial)
    ) %>%
    filter(PhaseRaw %in% names(phase_map)) %>%
    { if (exclude_warmup) filter(., !WarmUpFlag) else . } %>%
    { if (exclude_burnin) filter(., !BurnInFlag) else . } %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    { if (exclude_pm_trials) filter(., !PMTrialFlag) else . } %>%
    filter(
      !is.na(RT_ms), RT_ms >= rt_min_ms, RT_ms <= rt_max_ms,
      !is.na(CueConditionNorm), CueConditionNorm %in% cue_levels
    )
}

phase_session_note <- function(df) {
  ses_counts <- df %>%
    distinct(SessionNumInt, Phase) %>%
    count(Phase, name = "n_sessions")

  parts <- character(0)
  for (ph in phase_levels) {
    n <- ses_counts$n_sessions[ses_counts$Phase == ph]
    if (length(n) == 0 || is.na(n) || n == 0) {
      next
    }
    parts <- c(
      parts,
      paste0(ph, ": ", n, " session", if (n == 1) "" else "s")
    )
  }
  if (!length(parts)) {
    return("No phase sessions found")
  }
  paste0("Sessions included so far: ", paste(parts, collapse = " | "))
}

pm_order_tag <- function(raw_df) {
  ses_phase <- raw_df %>%
    mutate(
      SessionNumInt = suppressWarnings(as.integer(Session)),
      PhaseRaw = tolower(trimws(SessionPhase))
    ) %>%
    filter(!is.na(SessionNumInt), PhaseRaw %in% c("focal_pm", "nonfocal_pm")) %>%
    distinct(SessionNumInt, PhaseRaw) %>%
    arrange(SessionNumInt)

  if (nrow(ses_phase) == 0) {
    return("")
  }

  first_focal <- ses_phase$SessionNumInt[ses_phase$PhaseRaw == "focal_pm"]
  first_nonfocal <- ses_phase$SessionNumInt[ses_phase$PhaseRaw == "nonfocal_pm"]
  first_focal <- if (length(first_focal)) min(first_focal) else NA_integer_
  first_nonfocal <- if (length(first_nonfocal)) min(first_nonfocal) else NA_integer_

  if (is.na(first_focal) && is.na(first_nonfocal)) {
    return("")
  }
  if (is.na(first_focal)) {
    return("(nf only)")
  }
  if (is.na(first_nonfocal)) {
    return("(f only)")
  }
  if (first_focal < first_nonfocal) {
    "(f->nf)"
  } else {
    "(nf->f)"
  }
}

wilson_ci <- function(successes, n, z = 1.96) {
  if (n <= 0) {
    return(c(lower = NA_real_, upper = NA_real_))
  }
  p_hat <- successes / n
  z2_n <- z^2 / n
  center <- (p_hat + z2_n / 2) / (1 + z2_n)
  margin <- (z / (1 + z2_n)) * sqrt(p_hat * (1 - p_hat) / n + z2_n / (4 * n))
  c(lower = center - margin, upper = center + margin)
}

summarize_acc_by_phase_cue <- function(df) {
  df %>%
    filter(!is.na(ACC_num)) %>%
    group_by(Phase, CueConditionNorm) %>%
    summarize(
      n_trials = n(),
      n_correct = sum(ACC_num == 1, na.rm = TRUE),
      accuracy = n_correct / n_trials,
      .groups = "drop"
    ) %>%
    mutate(
      ci_lower = vapply(
        seq_len(n()),
        function(i) wilson_ci(n_correct[i], n_trials[i])["lower"],
        numeric(1)
      ),
      ci_upper = vapply(
        seq_len(n()),
        function(i) wilson_ci(n_correct[i], n_trials[i])["upper"],
        numeric(1)
      )
    ) %>%
    ungroup() %>%
    mutate(
      Phase = factor(Phase, levels = phase_levels),
      CueConditionNorm = factor(CueConditionNorm, levels = cue_levels)
    )
}

summarize_rt_by_phase_cue <- function(df) {
  df %>%
    group_by(Phase, CueConditionNorm) %>%
    summarize(
      median_rt = median(RT_ms, na.rm = TRUE),
      q25 = as.numeric(quantile(RT_ms, 0.25, na.rm = TRUE)),
      q75 = as.numeric(quantile(RT_ms, 0.75, na.rm = TRUE)),
      n_trials = n(),
      .groups = "drop"
    ) %>%
    mutate(
      Phase = factor(Phase, levels = phase_levels),
      CueConditionNorm = factor(CueConditionNorm, levels = cue_levels)
    )
}

make_rt_median_plot <- function(summary_df, subject_id, session_note, pm_tag) {
  y_min <- min(summary_df$q25, na.rm = TRUE)
  y_max <- max(summary_df$q75, na.rm = TRUE)
  y_pad <- max(25, 0.08 * (y_max - y_min))
  title_tag <- if (nzchar(pm_tag)) paste0(" ", pm_tag) else ""

  ggplot(summary_df, aes(x = CueConditionNorm, y = median_rt, color = Phase, group = Phase)) +
    geom_errorbar(
      aes(ymin = q25, ymax = q75),
      width = 0.12,
      linewidth = 0.8,
      alpha = 0.85
    ) +
    geom_line(linewidth = 1.1) +
    geom_point(size = 3.2) +
    scale_color_manual(values = phase_colors, drop = FALSE) +
    coord_cartesian(ylim = c(y_min - y_pad, y_max + y_pad)) +
    labs(
      title = paste0("Subject ", subject_id, ": median RT by phase and cue condition", title_tag),
      subtitle = paste0(
        "Points = median RT; bars = IQR (25th–75th percentile); ongoing-task trials only. ",
        session_note
      ),
      x = "Cue condition",
      y = "Median reaction time (ms)",
      color = "Phase"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 45, hjust = 1),
      legend.position = "bottom"
    )
}

make_accuracy_plot <- function(summary_df, subject_id, session_note, pm_tag) {
  y_min <- min(summary_df$ci_lower, na.rm = TRUE)
  y_max <- max(summary_df$ci_upper, na.rm = TRUE)
  y_pad <- max(0.005, 0.15 * (y_max - y_min))
  title_tag <- if (nzchar(pm_tag)) paste0(" ", pm_tag) else ""

  ggplot(summary_df, aes(x = CueConditionNorm, y = accuracy, color = Phase, group = Phase)) +
    geom_errorbar(
      aes(ymin = ci_lower, ymax = ci_upper),
      width = 0.12,
      linewidth = 0.8,
      alpha = 0.85
    ) +
    geom_line(linewidth = 1.1) +
    geom_point(size = 3.2) +
    scale_color_manual(values = phase_colors, drop = FALSE) +
    scale_y_continuous(labels = function(x) sprintf("%.3f", x)) +
    coord_cartesian(ylim = c(y_min - y_pad, min(1, y_max + y_pad))) +
    labs(
      title = paste0("Subject ", subject_id, ": accuracy by cue condition and phase", title_tag),
      subtitle = paste0(
        "Points = mean accuracy; bars = 95% Wilson CI; timeouts excluded. ",
        session_note
      ),
      x = "Cue condition",
      y = "Accuracy",
      color = "Phase"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 45, hjust = 1),
      legend.position = "bottom"
    )
}

analyze_subject <- function(data_dir, fig_root, subject_id) {
  raw_df <- read_subject_trials(data_dir, subject_id)
  if (is.null(raw_df) || nrow(raw_df) == 0) {
    warning("sub", subject_id, ": no trial files found; skipping.", call. = FALSE)
    return(invisible(NULL))
  }

  trial_df <- prepare_trials(raw_df)
  if (nrow(trial_df) == 0) {
    warning("sub", subject_id, ": no trials after filtering; skipping.", call. = FALSE)
    return(invisible(NULL))
  }

  summary_df <- summarize_rt_by_phase_cue(trial_df)
  acc_summary_df <- summarize_acc_by_phase_cue(trial_df)
  if (nrow(summary_df) == 0 || nrow(acc_summary_df) == 0) {
    warning("sub", subject_id, ": no phase × cue summaries; skipping.", call. = FALSE)
    return(invisible(NULL))
  }

  fig_dir <- file.path(fig_root, paste0("sub", subject_id))
  dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

  session_note <- phase_session_note(trial_df)
  pm_tag <- pm_order_tag(raw_df)
  rt_plot <- make_rt_median_plot(summary_df, subject_id, session_note, pm_tag)
  acc_plot <- make_accuracy_plot(acc_summary_df, subject_id, session_note, pm_tag)

  rt_file <- file.path(fig_dir, "rt_median_by_phase_cue.png")
  acc_file <- file.path(fig_dir, "accuracy_by_phase_cue.png")
  ggsave(rt_file, rt_plot, width = 10, height = 6.5, dpi = 300, bg = "white")
  ggsave(acc_file, acc_plot, width = 10, height = 6.5, dpi = 300, bg = "white")

  message(
    "sub", subject_id, pm_tag, ": saved RT + accuracy plots (",
    nrow(trial_df), " trials; phases: ",
    paste(intersect(phase_levels, unique(trial_df$Phase)), collapse = ", "), ")"
  )
  invisible(list(rt = rt_file, accuracy = acc_file))
}

proj_root <- find_project_root()
data_dir <- file.path(proj_root, "exp", "data_from_lab")
fig_root <- file.path(proj_root, "analysis", "fig")

cli_subjects <- suppressWarnings(as.integer(commandArgs(trailingOnly = TRUE)))
cli_subjects <- cli_subjects[!is.na(cli_subjects)]
subject_ids <- if (length(cli_subjects)) {
  sort(unique(cli_subjects))
} else {
  discover_subject_ids(data_dir, exclude_subject_ids)
}

if (!length(subject_ids)) {
  stop("No subject IDs to analyze.")
}

message("Analyzing subjects: ", paste(subject_ids, collapse = ", "))

for (sid in subject_ids) {
  analyze_subject(data_dir, fig_root, sid)
}

cat("Done.\n")
