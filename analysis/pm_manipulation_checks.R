# PM manipulation checks: hit rate, false alarms, monitoring cost, exclusions.
#
# Confirms that focal / nonfocal / PM-in-general are engaged:
#   1) PM hit rate by phase (focal vs nonfocal)
#   2) False-alarm / intrusion rate on non-PM trials
#   3) PM monitoring cost (ongoing-task RT: PM phase − baseline)
#   4) Methods exclusion checklist (hit <20%, baseline ACC <60%, RT<200ms >15%)
#
# Outputs under analysis/fig/ and analysis/fig/subXX/.
#
# Run from multiplecue-prospectiveM/ or analysis/:
#   Rscript analysis/pm_manipulation_checks.R
#   Rscript analysis/pm_manipulation_checks.R 17 28

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(ggplot2)
})

# ---- CONFIG ----
exclude_subject_ids <- c(100L)
subjects_per_page <- 9L
rt_min_ms <- 0
rt_max_ms <- 4000
exclude_warmup <- TRUE
exclude_burnin <- TRUE
exclude_timeouts <- TRUE
hit_rate_exclude_threshold <- 0.20
baseline_acc_exclude_threshold <- 0.60
anticipatory_rt_ms <- 200
anticipatory_rate_exclude_threshold <- 0.15
# ----------------

phase_levels <- c("Baseline", "Focal PM", "Nonfocal PM")
pm_phase_levels <- c("Focal PM", "Nonfocal PM")
phase_map <- c(
  baseline = "Baseline",
  focal_pm = "Focal PM",
  nonfocal_pm = "Nonfocal PM"
)
phase_colors <- c(
  "Baseline" = "#4C78A8",
  "Focal PM" = "#F58518",
  "Nonfocal PM" = "#54A24B"
)
cue_levels <- c("(1)", "(2)", "(3)", "(1,2)", "(1,3)", "(2,3)")

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

wilson_ci <- function(successes, n, z = 1.96) {
  if (is.na(n) || n <= 0) {
    return(c(lower = NA_real_, upper = NA_real_))
  }
  p_hat <- successes / n
  z2_n <- z^2 / n
  center <- (p_hat + z2_n / 2) / (1 + z2_n)
  margin <- (z / (1 + z2_n)) * sqrt(p_hat * (1 - p_hat) / n + z2_n / (4 * n))
  c(lower = center - margin, upper = center + margin)
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
    "CueCondition", "SessionPhase", "PMTrial", "PMKind", "PMACC",
    "PMIntrusion", "PMResponse", "PMPracticeBlock"
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

prepare_base_trials <- function(raw_df) {
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
      PMPracticeFlag = is_true_flag(PMPracticeBlock),
      TimeoutFlag = is_timeout_response(Response),
      PMTrialFlag = is_true_flag(PMTrial),
      PMHitFlag = is_true_flag(PMACC),
      FAFlag = is_true_flag(PMIntrusion) | (!is_true_flag(PMTrial) & is_true_flag(PMResponse)),
      AnticipatoryFlag = !is.na(RT_ms) & RT_ms < anticipatory_rt_ms
    ) %>%
    filter(PhaseRaw %in% names(phase_map)) %>%
    { if (exclude_warmup) filter(., !WarmUpFlag) else . } %>%
    { if (exclude_burnin) filter(., !BurnInFlag) else . } %>%
    filter(!PMPracticeFlag)
}

summarize_pm_hits <- function(df) {
  df %>%
    filter(Phase %in% pm_phase_levels, PMTrialFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    group_by(Phase) %>%
    summarize(
      n_pm = n(),
      n_hit = sum(PMHitFlag, na.rm = TRUE),
      hit_rate = ifelse(n_pm > 0, n_hit / n_pm, NA_real_),
      .groups = "drop"
    ) %>%
    mutate(
      ci_lower = vapply(seq_len(n()), function(i) wilson_ci(n_hit[i], n_pm[i])["lower"], numeric(1)),
      ci_upper = vapply(seq_len(n()), function(i) wilson_ci(n_hit[i], n_pm[i])["upper"], numeric(1)),
      Phase = factor(Phase, levels = pm_phase_levels)
    )
}

summarize_false_alarms <- function(df) {
  df %>%
    filter(Phase %in% phase_levels, !PMTrialFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    group_by(Phase) %>%
    summarize(
      n_non_pm = n(),
      n_fa = sum(FAFlag, na.rm = TRUE),
      fa_rate = ifelse(n_non_pm > 0, n_fa / n_non_pm, NA_real_),
      .groups = "drop"
    ) %>%
    mutate(
      ci_lower = vapply(seq_len(n()), function(i) wilson_ci(n_fa[i], n_non_pm[i])["lower"], numeric(1)),
      ci_upper = vapply(seq_len(n()), function(i) wilson_ci(n_fa[i], n_non_pm[i])["upper"], numeric(1)),
      Phase = factor(Phase, levels = phase_levels)
    )
}

summarize_ongoing_rt <- function(df) {
  df %>%
    filter(!PMTrialFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    filter(!is.na(RT_ms), RT_ms >= rt_min_ms, RT_ms <= rt_max_ms) %>%
    group_by(Phase) %>%
    summarize(
      n_trials = n(),
      median_rt = median(RT_ms, na.rm = TRUE),
      mean_rt = mean(RT_ms, na.rm = TRUE),
      q25 = as.numeric(quantile(RT_ms, 0.25, na.rm = TRUE)),
      q75 = as.numeric(quantile(RT_ms, 0.75, na.rm = TRUE)),
      .groups = "drop"
    ) %>%
    mutate(Phase = factor(Phase, levels = phase_levels))
}

summarize_ongoing_acc <- function(df) {
  df %>%
    filter(!PMTrialFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    filter(!is.na(ACC_num)) %>%
    group_by(Phase) %>%
    summarize(
      n_trials = n(),
      n_correct = sum(ACC_num == 1, na.rm = TRUE),
      accuracy = n_correct / n_trials,
      .groups = "drop"
    ) %>%
    mutate(
      ci_lower = vapply(seq_len(n()), function(i) wilson_ci(n_correct[i], n_trials[i])["lower"], numeric(1)),
      ci_upper = vapply(seq_len(n()), function(i) wilson_ci(n_correct[i], n_trials[i])["upper"], numeric(1)),
      Phase = factor(Phase, levels = phase_levels)
    )
}

compute_monitoring_cost <- function(rt_by_phase) {
  base_rt <- rt_by_phase$median_rt[rt_by_phase$Phase == "Baseline"]
  if (!length(base_rt) || is.na(base_rt[1])) {
    return(tibble(
      Phase = factor(character(0), levels = pm_phase_levels),
      baseline_median_rt = numeric(0),
      phase_median_rt = numeric(0),
      cost_ms = numeric(0),
      n_trials = integer(0)
    ))
  }
  base_rt <- base_rt[1]
  rt_by_phase %>%
    filter(Phase %in% pm_phase_levels) %>%
    transmute(
      Phase = factor(as.character(Phase), levels = pm_phase_levels),
      baseline_median_rt = base_rt,
      phase_median_rt = median_rt,
      cost_ms = median_rt - base_rt,
      n_trials = n_trials
    )
}

exclusion_checklist <- function(df) {
  # Hit rate by PM phase
  hits <- summarize_pm_hits(df)
  hit_focal <- hits$hit_rate[hits$Phase == "Focal PM"]
  hit_nonfocal <- hits$hit_rate[hits$Phase == "Nonfocal PM"]
  hit_focal <- if (length(hit_focal)) hit_focal[1] else NA_real_
  hit_nonfocal <- if (length(hit_nonfocal)) hit_nonfocal[1] else NA_real_

  fail_hit_focal <- !is.na(hit_focal) && hit_focal < hit_rate_exclude_threshold
  fail_hit_nonfocal <- !is.na(hit_nonfocal) && hit_nonfocal < hit_rate_exclude_threshold

  # Baseline ongoing accuracy
  base_acc_df <- df %>%
    filter(Phase == "Baseline", !PMTrialFlag) %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    filter(!is.na(ACC_num))
  baseline_acc <- if (nrow(base_acc_df)) mean(base_acc_df$ACC_num == 1) else NA_real_
  fail_baseline_acc <- !is.na(baseline_acc) && baseline_acc < baseline_acc_exclude_threshold

  # Anticipatory responses across analyzed phases
  rt_df <- df %>%
    { if (exclude_timeouts) filter(., !TimeoutFlag) else . } %>%
    filter(!is.na(RT_ms), RT_ms <= rt_max_ms)
  anticipatory_rate <- if (nrow(rt_df)) mean(rt_df$AnticipatoryFlag) else NA_real_
  fail_anticipatory <- !is.na(anticipatory_rate) &&
    anticipatory_rate > anticipatory_rate_exclude_threshold

  tibble(
    hit_rate_focal = hit_focal,
    hit_rate_nonfocal = hit_nonfocal,
    baseline_acc = baseline_acc,
    anticipatory_rate = anticipatory_rate,
    fail_hit_focal = fail_hit_focal,
    fail_hit_nonfocal = fail_hit_nonfocal,
    fail_baseline_acc = fail_baseline_acc,
    fail_anticipatory = fail_anticipatory,
    exclude_flag = fail_hit_focal | fail_hit_nonfocal | fail_baseline_acc | fail_anticipatory,
    exclude_reason = paste(
      c(
        if (fail_hit_focal) "hit_focal<20%" else NULL,
        if (fail_hit_nonfocal) "hit_nonfocal<20%" else NULL,
        if (fail_baseline_acc) "baseline_acc<60%" else NULL,
        if (fail_anticipatory) "anticipatory>15%" else NULL
      ),
      collapse = "; "
    )
  )
}

facet_ncol_for <- function(n) {
  if (n <= 3) n else 3L
}

chunk_vector <- function(x, size) {
  if (!length(x)) {
    return(list())
  }
  split(x, ceiling(seq_along(x) / size))
}

make_rate_bar_plot <- function(summary_df, y_col, ymin_col, ymax_col, title, subtitle, ylab) {
  ggplot(summary_df, aes(x = Phase, y = .data[[y_col]], fill = Phase)) +
    geom_col(width = 0.7, alpha = 0.9) +
    geom_errorbar(
      aes(ymin = .data[[ymin_col]], ymax = .data[[ymax_col]]),
      width = 0.15,
      linewidth = 0.7
    ) +
    geom_text(
      aes(label = sprintf("%.1f%%\n(n=%d)", 100 * .data[[y_col]],
                          if ("n_pm" %in% names(summary_df)) n_pm else n_non_pm)),
      vjust = -0.2,
      size = 3.2,
      lineheight = 0.9
    ) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    scale_y_continuous(labels = function(x) sprintf("%.0f%%", 100 * x),
                       limits = c(0, min(1.05, max(summary_df[[ymax_col]], na.rm = TRUE) + 0.12))) +
    labs(title = title, subtitle = subtitle, x = NULL, y = ylab, fill = "Phase") +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "none",
      axis.text.x = element_text(angle = 20, hjust = 1)
    )
}

make_cost_bar_plot <- function(cost_df, title, subtitle) {
  ggplot(cost_df, aes(x = Phase, y = cost_ms, fill = Phase)) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    geom_col(width = 0.7, alpha = 0.9) +
    geom_text(
      aes(label = sprintf("%+.0f ms", cost_ms),
          vjust = ifelse(cost_ms >= 0, -0.4, 1.3)),
      size = 3.4
    ) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    labs(
      title = title,
      subtitle = subtitle,
      x = NULL,
      y = "Monitoring cost (ms)\nmedian RT(PM phase) − median RT(baseline)",
      fill = "Phase"
    ) +
    theme_minimal(base_size = 14) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "none",
      axis.text.x = element_text(angle = 20, hjust = 1)
    )
}

make_group_hit_plot <- function(hit_df) {
  ggplot(hit_df, aes(x = SubjectLabel, y = hit_rate, fill = Phase)) +
    geom_col(position = position_dodge(width = 0.8), width = 0.72, alpha = 0.92) +
    geom_errorbar(
      aes(ymin = ci_lower, ymax = ci_upper),
      position = position_dodge(width = 0.8),
      width = 0.15,
      linewidth = 0.55
    ) +
    geom_hline(yintercept = hit_rate_exclude_threshold, linetype = "dashed",
               color = "grey30", linewidth = 0.6) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    scale_y_continuous(labels = function(x) sprintf("%.0f%%", 100 * x), limits = c(0, 1.05)) +
    labs(
      title = "PM hit rate by subject and phase",
      subtitle = paste0(
        "Dashed line = methods exclusion threshold (",
        100 * hit_rate_exclude_threshold,
        "%). Bars = hit rate; error bars = 95% Wilson CI."
      ),
      x = NULL,
      y = "PM hit rate",
      fill = "Phase"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 45, hjust = 1),
      legend.position = "bottom"
    )
}

make_group_fa_plot <- function(fa_df) {
  fa_pm <- fa_df %>% filter(Phase %in% pm_phase_levels)
  ggplot(fa_pm, aes(x = SubjectLabel, y = fa_rate, fill = Phase)) +
    geom_col(position = position_dodge(width = 0.8), width = 0.72, alpha = 0.92) +
    geom_errorbar(
      aes(ymin = ci_lower, ymax = ci_upper),
      position = position_dodge(width = 0.8),
      width = 0.15,
      linewidth = 0.55
    ) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    scale_y_continuous(labels = function(x) sprintf("%.2f%%", 100 * x)) +
    labs(
      title = "PM false-alarm (intrusion) rate by subject and phase",
      subtitle = "Non-PM trials only; FA = PMIntrusion or spacebar on non-PM trial. Error bars = 95% Wilson CI.",
      x = NULL,
      y = "False-alarm rate",
      fill = "Phase"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 45, hjust = 1),
      legend.position = "bottom"
    )
}

make_group_cost_plot <- function(cost_df) {
  ggplot(cost_df, aes(x = SubjectLabel, y = cost_ms, fill = Phase)) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    geom_col(position = position_dodge(width = 0.8), width = 0.72, alpha = 0.92) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    labs(
      title = "PM monitoring cost by subject (ongoing-task median RT)",
      subtitle = "Cost = median RT in PM phase − median RT in baseline (non-PM trials only).",
      x = NULL,
      y = "Monitoring cost (ms)",
      fill = "Phase"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(face = "bold"),
      axis.text.x = element_text(angle = 45, hjust = 1),
      legend.position = "bottom"
    )
}

make_group_mean_summary_plot <- function(hit_df, fa_df, cost_df) {
  hit_sum <- hit_df %>%
    group_by(Phase) %>%
    summarize(
      mean_val = mean(hit_rate, na.rm = TRUE),
      se = sd(hit_rate, na.rm = TRUE) / sqrt(sum(!is.na(hit_rate))),
      n = sum(!is.na(hit_rate)),
      measure = "PM hit rate",
      .groups = "drop"
    )
  fa_sum <- fa_df %>%
    filter(Phase %in% pm_phase_levels) %>%
    group_by(Phase) %>%
    summarize(
      mean_val = mean(fa_rate, na.rm = TRUE),
      se = sd(fa_rate, na.rm = TRUE) / sqrt(sum(!is.na(fa_rate))),
      n = sum(!is.na(fa_rate)),
      measure = "False-alarm rate",
      .groups = "drop"
    )
  cost_sum <- cost_df %>%
    group_by(Phase) %>%
    summarize(
      mean_val = mean(cost_ms, na.rm = TRUE),
      se = sd(cost_ms, na.rm = TRUE) / sqrt(sum(!is.na(cost_ms))),
      n = sum(!is.na(cost_ms)),
      measure = "Monitoring cost (ms)",
      .groups = "drop"
    )

  rate_df <- bind_rows(hit_sum, fa_sum) %>%
    mutate(Phase = factor(as.character(Phase), levels = pm_phase_levels))
  cost_sum <- cost_sum %>%
    mutate(Phase = factor(as.character(Phase), levels = pm_phase_levels))

  p_rate <- ggplot(rate_df, aes(x = Phase, y = mean_val, fill = Phase)) +
    geom_col(width = 0.7, alpha = 0.9) +
    geom_errorbar(aes(ymin = mean_val - se, ymax = mean_val + se), width = 0.15) +
    facet_wrap(~measure, scales = "free_y") +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    scale_y_continuous(labels = function(x) sprintf("%.1f%%", 100 * x)) +
    labs(
      title = "Group means: PM engagement checks",
      subtitle = "Mean ± SE across subjects with data in that phase.",
      x = NULL,
      y = NULL,
      fill = "Phase"
    ) +
    theme_minimal(base_size = 13) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "bottom",
      strip.text = element_text(face = "bold")
    )

  p_cost <- ggplot(cost_sum, aes(x = Phase, y = mean_val, fill = Phase)) +
    geom_hline(yintercept = 0, linewidth = 0.6, color = "grey40") +
    geom_col(width = 0.7, alpha = 0.9) +
    geom_errorbar(aes(ymin = mean_val - se, ymax = mean_val + se), width = 0.15) +
    geom_text(aes(label = sprintf("%+.0f ms\n(n=%d)", mean_val, n)),
              vjust = ifelse(cost_sum$mean_val >= 0, -0.3, 1.2), size = 3.3, lineheight = 0.9) +
    scale_fill_manual(values = phase_colors, drop = FALSE) +
    labs(
      title = "Group mean monitoring cost",
      subtitle = "Mean ± SE of subject-level median-RT costs (PM − baseline).",
      x = NULL,
      y = "Cost (ms)",
      fill = "Phase"
    ) +
    theme_minimal(base_size = 13) +
    theme(
      plot.title = element_text(face = "bold"),
      legend.position = "none"
    )

  list(rates = p_rate, cost = p_cost)
}

analyze_subject <- function(data_dir, fig_root, subject_id) {
  raw_df <- read_subject_trials(data_dir, subject_id)
  if (is.null(raw_df) || nrow(raw_df) == 0) {
    warning("sub", subject_id, ": no trial files; skipping.", call. = FALSE)
    return(invisible(NULL))
  }

  df <- prepare_base_trials(raw_df)
  if (nrow(df) == 0) {
    warning("sub", subject_id, ": no trials after filtering; skipping.", call. = FALSE)
    return(invisible(NULL))
  }

  pm_tag <- pm_order_tag(raw_df)
  subject_label <- if (nzchar(pm_tag)) {
    paste0("Subject ", subject_id, " ", pm_tag)
  } else {
    paste0("Subject ", subject_id)
  }
  title_tag <- if (nzchar(pm_tag)) paste0(" ", pm_tag) else ""

  hits <- summarize_pm_hits(df)
  fas <- summarize_false_alarms(df)
  rt_phase <- summarize_ongoing_rt(df)
  acc_phase <- summarize_ongoing_acc(df)
  costs <- compute_monitoring_cost(rt_phase)
  excl <- exclusion_checklist(df) %>%
    mutate(SubjectId = subject_id, SubjectLabel = subject_label, .before = 1)

  fig_dir <- file.path(fig_root, paste0("sub", subject_id))
  dir.create(fig_dir, recursive = TRUE, showWarnings = FALSE)

  if (nrow(hits) > 0) {
    p_hit <- make_rate_bar_plot(
      hits, "hit_rate", "ci_lower", "ci_upper",
      paste0("Subject ", subject_id, ": PM hit rate", title_tag),
      "PM trials only; ACC = PMACC. Bars = hit rate; error bars = 95% Wilson CI.",
      "PM hit rate"
    )
    ggsave(
      file.path(fig_dir, "pm_hit_rate_by_phase.png"),
      p_hit, width = 8, height = 5.5, dpi = 300, bg = "white"
    )
  }

  if (nrow(fas) > 0) {
    fas_plot <- fas %>% filter(Phase %in% pm_phase_levels | n_fa > 0)
    if (nrow(fas_plot) > 0) {
      p_fa <- make_rate_bar_plot(
        fas_plot, "fa_rate", "ci_lower", "ci_upper",
        paste0("Subject ", subject_id, ": PM false-alarm rate", title_tag),
        "Non-PM trials; FA = intrusion / spacebar on non-PM. Error bars = 95% Wilson CI.",
        "False-alarm rate"
      )
      ggsave(
        file.path(fig_dir, "pm_false_alarm_by_phase.png"),
        p_fa, width = 8, height = 5.5, dpi = 300, bg = "white"
      )
    }
  }

  if (nrow(costs) > 0) {
    p_cost <- make_cost_bar_plot(
      costs,
      paste0("Subject ", subject_id, ": PM monitoring cost", title_tag),
      "Ongoing-task (non-PM) median RT relative to baseline."
    )
    ggsave(
      file.path(fig_dir, "pm_monitoring_cost_by_phase.png"),
      p_cost, width = 8, height = 5.5, dpi = 300, bg = "white"
    )
  }

  if (nrow(acc_phase) > 0) {
    p_acc <- ggplot(acc_phase, aes(x = Phase, y = accuracy, fill = Phase)) +
      geom_col(width = 0.7, alpha = 0.9) +
      geom_errorbar(aes(ymin = ci_lower, ymax = ci_upper), width = 0.15) +
      scale_fill_manual(values = phase_colors, drop = FALSE) +
      scale_y_continuous(labels = function(x) sprintf("%.0f%%", 100 * x), limits = c(0, 1.05)) +
      labs(
        title = paste0("Subject ", subject_id, ": ongoing-task accuracy by phase", title_tag),
        subtitle = "Non-PM trials; error bars = 95% Wilson CI.",
        x = NULL, y = "Accuracy", fill = "Phase"
      ) +
      theme_minimal(base_size = 14) +
      theme(
        plot.title = element_text(face = "bold"),
        legend.position = "none",
        axis.text.x = element_text(angle = 20, hjust = 1)
      )
    ggsave(
      file.path(fig_dir, "ongoing_accuracy_by_phase.png"),
      p_acc, width = 8, height = 5.5, dpi = 300, bg = "white"
    )
  }

  message(
    "sub", subject_id, title_tag, ": PM checks saved",
    if (nrow(hits)) {
      paste0(
        " | hits: ",
        paste(sprintf("%s=%.1f%%", hits$Phase, 100 * hits$hit_rate), collapse = ", ")
      )
    } else {
      " | no PM trials"
    },
    if (excl$exclude_flag[1]) paste0(" | EXCLUDE? ", excl$exclude_reason[1]) else ""
  )

  invisible(list(
    subject_id = subject_id,
    subject_label = subject_label,
    hits = hits %>% mutate(SubjectId = subject_id, SubjectLabel = subject_label),
    fas = fas %>% mutate(SubjectId = subject_id, SubjectLabel = subject_label),
    costs = costs %>% mutate(SubjectId = subject_id, SubjectLabel = subject_label),
    rt_phase = rt_phase %>% mutate(SubjectId = subject_id, SubjectLabel = subject_label),
    acc_phase = acc_phase %>% mutate(SubjectId = subject_id, SubjectLabel = subject_label),
    exclusion = excl
  ))
}

# ---- main ----
proj_root <- find_project_root()
data_dir <- file.path(proj_root, "exp", "data_from_lab")
fig_root <- file.path(proj_root, "analysis", "fig")
out_csv_dir <- file.path(proj_root, "analysis", "fig")

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

message("PM manipulation checks for subjects: ", paste(subject_ids, collapse = ", "))

all_hits <- list()
all_fas <- list()
all_costs <- list()
all_excl <- list()

for (sid in subject_ids) {
  res <- analyze_subject(data_dir, fig_root, sid)
  if (!is.null(res)) {
    all_hits[[as.character(sid)]] <- res$hits
    all_fas[[as.character(sid)]] <- res$fas
    all_costs[[as.character(sid)]] <- res$costs
    all_excl[[as.character(sid)]] <- res$exclusion
  }
}

if (!length(all_excl)) {
  stop("No subjects produced usable summaries.")
}

hit_all <- bind_rows(all_hits)
fa_all <- bind_rows(all_fas)
cost_all <- bind_rows(all_costs)
excl_all <- bind_rows(all_excl)

# Subject-label factor ordered by id
label_levels <- excl_all %>%
  arrange(SubjectId) %>%
  pull(SubjectLabel) %>%
  unique()

if (nrow(hit_all)) {
  hit_all <- hit_all %>%
    mutate(SubjectLabel = factor(SubjectLabel, levels = label_levels))
  ggsave(
    file.path(fig_root, "pm_hit_rate_all_subjects.png"),
    make_group_hit_plot(hit_all),
    width = max(10, 0.7 * n_distinct(hit_all$SubjectId) + 4),
    height = 6.5,
    dpi = 300,
    bg = "white"
  )
  message("Saved: pm_hit_rate_all_subjects.png")
}

if (nrow(fa_all)) {
  fa_all <- fa_all %>%
    mutate(SubjectLabel = factor(SubjectLabel, levels = label_levels))
  ggsave(
    file.path(fig_root, "pm_false_alarm_all_subjects.png"),
    make_group_fa_plot(fa_all),
    width = max(10, 0.7 * n_distinct(fa_all$SubjectId) + 4),
    height = 6.5,
    dpi = 300,
    bg = "white"
  )
  message("Saved: pm_false_alarm_all_subjects.png")
}

if (nrow(cost_all)) {
  cost_all <- cost_all %>%
    mutate(SubjectLabel = factor(SubjectLabel, levels = label_levels))
  ggsave(
    file.path(fig_root, "pm_monitoring_cost_all_subjects.png"),
    make_group_cost_plot(cost_all),
    width = max(10, 0.7 * n_distinct(cost_all$SubjectId) + 4),
    height = 6.5,
    dpi = 300,
    bg = "white"
  )
  message("Saved: pm_monitoring_cost_all_subjects.png")
}

if (nrow(hit_all) && nrow(cost_all)) {
  gsum <- make_group_mean_summary_plot(hit_all, fa_all, cost_all)
  ggsave(
    file.path(fig_root, "pm_manipulation_group_means_rates.png"),
    gsum$rates, width = 10, height = 5.5, dpi = 300, bg = "white"
  )
  ggsave(
    file.path(fig_root, "pm_manipulation_group_means_cost.png"),
    gsum$cost, width = 7.5, height = 5.5, dpi = 300, bg = "white"
  )
  message("Saved: pm_manipulation_group_means_rates.png / _cost.png")
}

# Combined subject table
summary_wide <- excl_all %>%
  left_join(
    hit_all %>%
      select(SubjectId, Phase, hit_rate, n_pm, n_hit) %>%
      pivot_wider(
        names_from = Phase,
        values_from = c(hit_rate, n_pm, n_hit),
        names_sep = "_"
      ),
    by = "SubjectId"
  ) %>%
  left_join(
    fa_all %>%
      filter(Phase %in% pm_phase_levels) %>%
      select(SubjectId, Phase, fa_rate, n_fa) %>%
      pivot_wider(
        names_from = Phase,
        values_from = c(fa_rate, n_fa),
        names_sep = "_"
      ),
    by = "SubjectId"
  ) %>%
  left_join(
    cost_all %>%
      select(SubjectId, Phase, cost_ms) %>%
      pivot_wider(
        names_from = Phase,
        values_from = cost_ms,
        names_prefix = "cost_ms_"
      ),
    by = "SubjectId"
  )

csv_path <- file.path(out_csv_dir, "pm_manipulation_checks_summary.csv")
write.csv(summary_wide, csv_path, row.names = FALSE)
message("Saved summary table: ", csv_path)

n_exclude <- sum(excl_all$exclude_flag, na.rm = TRUE)
cat(
  "Done. Subjects analyzed: ", nrow(excl_all),
  "; flagged by methods exclusions: ", n_exclude, "\n",
  sep = ""
)
if (n_exclude > 0) {
  flagged <- excl_all %>% filter(exclude_flag)
  cat(
    "Flagged: ",
    paste(sprintf("%s [%s]", flagged$SubjectLabel, flagged$exclude_reason), collapse = "; "),
    "\n",
    sep = ""
  )
}
