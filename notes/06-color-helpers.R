# Supporting code for 06-color.qmd. Source after loading tidyverse,
# colorspace, and patchwork. Color construction and scale choices stay in the note.

# Shared styling: ordinary plots inherit the global theme; diagrams opt out of axes.
theme_set(
    theme_classic() +
        theme(
            panel.border = element_rect(fill = NA, linewidth = 0),
            plot.title = element_text(size = 10)
        )
)
theme_diagram <- theme_void() +
    theme(legend.position = "none", plot.title = element_text(size = 10))
theme_swatch <- theme_void() +
    theme(
        axis.text.y = element_text(hjust = 1, margin = margin(r = 4)),
        strip.text = element_text(hjust = 0, size = 9, margin = margin(b = 4)),
        plot.title = element_text(size = 10)
    )
theme_swatch_labeled <- theme_swatch + theme(axis.text.x = element_text(size = 8))
theme_bins <- theme_swatch + theme(axis.text.y = element_blank())
theme_wheel <- theme_diagram + theme(plot.title = element_text(hjust = 0.5))
theme_scatter <- theme(
    legend.position = "none", axis.text = element_blank(), axis.ticks = element_blank()
)
theme_colorbar <- theme(legend.position = "bottom", legend.key.width = unit(0.8, "cm"))
theme_map <- theme_diagram +
    theme(
        legend.position = "bottom", legend.title = element_blank(),
        legend.key.width = unit(0.6, "cm"), legend.key.height = unit(0.2, "cm"),
        plot.title = element_text(size = 9), legend.text = element_text(size = 7)
    )
theme_bivariate_legend <- theme_minimal(base_size = 9) +
    theme(panel.grid = element_blank(), axis.text = element_blank())

# Example data. Keep random draws together so a fresh render is reproducible.
set.seed(2026)
wheel <- expand_grid(hue = seq(0, 359, by = 1), sat = seq(0.05, 1, by = 0.05))
channel_points <- tibble(x = runif(300), y = runif(300), value = x + y)
cells <- expand_grid(x = 1:12, y = 1:12) |>
    mutate(level = factor(cut(x + y + rnorm(n(), sd = 2), 3, labels = FALSE)))
hue_counts <- c(3, 6, 12, 20)
hue_points <- map_dfr(hue_counts, \(k) {
    group <- sample(k, 200, replace = TRUE)
    tibble(k = k, group = group, x = runif(200), y = runif(200))
})
clusters <- tibble(category = 1:12, angle = 2 * pi * (category - 1) / 12) |>
    mutate(cx = cos(angle), cy = sin(angle))
category_points <- clusters |>
    slice(rep(1:12, each = 12)) |>
    mutate(x = cx + rnorm(n(), sd = 0.12), y = cy + rnorm(n(), sd = 0.12))

# as.vector() flattens matrices column by column; expand_grid() varies row fastest.
elev <- expand_grid(col = 1:ncol(volcano), row = 1:nrow(volcano)) |>
    mutate(z = as.vector(volcano))
shift_rows <- rbind(volcano[-1, ], volcano[nrow(volcano), ])
shift_cols <- cbind(volcano[, -1], volcano[, ncol(volcano)])
elev$slope <- as.vector(sqrt((shift_rows - volcano)^2 + (shift_cols - volcano)^2))

# Repeated figure scaffolding. The scales themselves are supplied in the note.
wheel_plot <- function(colors, title) {
    ggplot(wheel, aes(hue, sat, fill = colors, color = colors)) +
        geom_tile() +
        scale_fill_identity() +
        scale_color_identity() +
        scale_x_continuous(limits = c(-0.5, 359.5)) +
        coord_polar() +
        labs(title = title) +
        theme_wheel
}

map_plot <- function(scale, title, data = elev) {
    ggplot(data, aes(col, row, fill = z)) +
        geom_tile() +
        scale +
        coord_equal() +
        labs(title = title) +
        theme_map
}

# Contrast utilities for choosing demonstration text colors on white.
relative_luminance <- function(color) {
    rgb <- col2rgb(color) / 255
    linear <- ifelse(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055)^2.4)
    colSums(linear * c(0.2126, 0.7152, 0.0722))
}

contrast_ratio <- function(a, b) {
    la <- relative_luminance(a)
    lb <- relative_luminance(b)
    (pmax(la, lb) + 0.05) / (pmin(la, lb) + 0.05)
}

text_color <- function(target) {
    grays <- gray(seq(0, 1, length.out = 256))
    grays[which.min(abs(contrast_ratio(grays, "white") - target))]
}

contrast_examples <- tibble(ratio = c(1.5, 3, 10)) |>
    mutate(
        color = map_chr(ratio, text_color),
        label = paste0("Contrast ", ratio, ":1 (", round(contrast_ratio(color, "white"), 1), " achieved)")
    )
