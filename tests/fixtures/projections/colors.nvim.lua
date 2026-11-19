local M = {}

M.name = "dotfiles"
M.mode = "dark"

local p = {
  background = "#000000",
  foreground = "#fbd0aa",
  accent = "#26201a",
  accent_muted = "#000000",
  surface = "#000000",
  on_surface = "#fbd0aa",
  error = "#26201a",
  warning = "#cdaa8a",
  primary = "#26201a",
  on_primary = "#806a57",
  primary_container = "#4d4034",
  on_primary_container = "#cdaa8a",
  secondary = "#000000",
  secondary_container = "#26201a",
  on_secondary_container = "#4d4034",
  tertiary = "#cdaa8a",
  on_tertiary = "#26201a",
  tertiary_container = "#fbd0aa",
  on_tertiary_container = "#4d4034",
  error_container = "#4d4034",
  on_error = "#26201a",
  on_error_container = "#4d4034",
  outline = "#fbd0aa",
  outline_variant = "#000000",
  on_surface_variant = "#000000",
  surface_container = "#4d4034",
  surface_container_high = "#806a57",
  surface_container_low = "#fbd0aa",
  primary_fixed_dim = "#cdaa8a",
}

M.palette = {
  background = p.background,
  foreground = p.foreground,
  accent = p.accent,
  accent_muted = p.accent_muted,
  surface = p.surface,
  on_surface = p.on_surface,
  error = p.error,
  warning = p.warning,
  primary = p.primary,
  on_primary = p.on_primary,
  primary_container = p.primary_container,
  on_primary_container = p.on_primary_container,
  secondary = p.secondary,
  secondary_container = p.secondary_container,
  on_secondary_container = p.on_secondary_container,
  tertiary = p.tertiary,
  on_tertiary = p.on_tertiary,
  tertiary_container = p.tertiary_container,
  on_tertiary_container = p.on_tertiary_container,
  error_container = p.error_container,
  on_error = p.on_error,
  on_error_container = p.on_error_container,
  outline = p.outline,
  outline_variant = p.outline_variant,
  on_surface_variant = p.on_surface_variant,
  surface_container = p.surface_container,
  surface_container_high = p.surface_container_high,
  surface_container_low = p.surface_container_low,
  primary_fixed_dim = p.primary_fixed_dim,
  ansi = {
    "#000000",
    "#26201a",
    "#cdaa8a",
    "#000000",
    "#26201a",
    "#806a57",
    "#000000",
    "#fbd0aa",
    "#fbd0aa",
    "#4d4034",
    "#fbd0aa",
    "#26201a",
    "#4d4034",
    "#4d4034",
    "#806a57",
    "#000000",
  },
}

M.highlights = {}
local function hl(group, attrs)
  M.highlights[group] = attrs
end

-- Core editor
hl("Normal", { fg = p.foreground, bg = p.background })
hl("NormalNC", { fg = p.foreground, bg = p.background })
hl("NormalFloat", { fg = p.on_surface, bg = p.surface_container })
hl("FloatBorder", { fg = p.outline, bg = p.surface_container })
hl("Cursor", { fg = p.background, bg = p.primary })
hl("lCursor", { fg = p.background, bg = p.primary })
hl("TermCursor", { fg = p.background, bg = p.primary })
hl("Visual", { bg = p.primary_container })
hl("Search", { fg = p.on_tertiary_container, bg = p.tertiary_container })
hl("IncSearch", { fg = p.on_primary, bg = p.primary })
hl("CurSearch", { fg = p.on_tertiary_container, bg = p.tertiary })
hl("Pmenu", { fg = p.on_surface, bg = p.surface_container_high })
hl("PmenuSel", { fg = p.on_secondary_container, bg = p.secondary_container })
hl("PmenuSbar", { bg = p.surface_container })
hl("PmenuThumb", { bg = p.outline_variant })
hl("StatusLine", { fg = p.on_surface, bg = p.surface_container_high })
hl("StatusLineNC", { fg = p.on_surface_variant, bg = p.surface_container })
hl("TabLine", { fg = p.on_surface_variant, bg = p.surface_container })
hl("TabLineSel", { fg = p.on_secondary_container, bg = p.secondary_container })
hl("TabLineFill", { bg = p.surface_container })
hl("WinSeparator", { fg = p.outline_variant, bg = p.background })
hl("VertSplit", { fg = p.outline_variant, bg = p.background })
hl("LineNr", { fg = p.on_surface_variant })
hl("CursorLineNr", { fg = p.primary, bold = true })
hl("SignColumn", { fg = p.on_surface_variant, bg = p.background })
hl("Folded", { fg = p.on_surface_variant, bg = p.surface_container })
hl("ColorColumn", { bg = p.surface_container })
hl("CursorLine", { bg = p.surface_container_low })

-- Syntax
hl("Comment", { fg = p.on_surface_variant, italic = true })
hl("Constant", { fg = p.tertiary })
hl("Number", { fg = p.tertiary })
hl("Boolean", { fg = p.tertiary })
hl("Character", { fg = p.tertiary })
hl("String", { fg = p.secondary })
hl("Identifier", { fg = p.primary })
hl("Function", { fg = p.primary })
hl("Statement", { fg = p.tertiary })
hl("Keyword", { fg = p.tertiary })
hl("Operator", { fg = p.tertiary })
hl("PreProc", { fg = p.tertiary })
hl("Type", { fg = p.secondary })
hl("StorageClass", { fg = p.secondary })
hl("Structure", { fg = p.secondary })
hl("Special", { fg = p.primary_fixed_dim })
hl("SpecialChar", { fg = p.primary_fixed_dim })
hl("Delimiter", { fg = p.primary_fixed_dim })

-- Diagnostics, diff, messages
hl("Error", { fg = p.error, bold = true })
hl("ErrorMsg", { fg = p.error, bold = true })
hl("WarningMsg", { fg = p.warning })
hl("Todo", { fg = p.on_primary_container, bg = p.primary_container, bold = true })
hl("DiffAdd", { bg = p.tertiary_container })
hl("DiffChange", { bg = p.secondary_container })
hl("DiffDelete", { fg = p.on_error_container, bg = p.error_container })
hl("DiffText", { bg = p.secondary })
hl("DiagnosticError", { fg = p.error })
hl("DiagnosticWarn", { fg = p.warning })
hl("DiagnosticInfo", { fg = p.secondary })
hl("DiagnosticHint", { fg = p.tertiary })
hl("DiagnosticUnderlineError", { sp = p.error, underline = true })
hl("DiagnosticUnderlineWarn", { sp = p.warning, underline = true })
hl("DiagnosticUnderlineInfo", { sp = p.secondary, underline = true })
hl("DiagnosticUnderlineHint", { sp = p.tertiary, underline = true })
hl("LspReferenceText", { bg = p.surface_container_high })
hl("LspReferenceRead", { bg = p.surface_container_high })
hl("LspReferenceWrite", { bg = p.surface_container_high })

-- Treesitter/LSP aliases
M.links = {
  ["@comment"] = "Comment",
  ["@string"] = "String",
  ["@number"] = "Number",
  ["@boolean"] = "Boolean",
  ["@function"] = "Function",
  ["@function.call"] = "Function",
  ["@keyword"] = "Keyword",
  ["@keyword.function"] = "Keyword",
  ["@operator"] = "Operator",
  ["@type"] = "Type",
  ["@type.builtin"] = "Type",
  ["@variable"] = "Identifier",
  ["@variable.parameter"] = "Identifier",
  ["@constant"] = "Constant",
  ["@constant.builtin"] = "Constant",
  ["@property"] = "Identifier",
  ["@punctuation.delimiter"] = "Delimiter",
  ["@punctuation.bracket"] = "Delimiter",
  ["@markup.heading"] = "Todo",
  ["@markup.link"] = "Special",
  ["@diagnostic.error"] = "DiagnosticError",
  ["@diagnostic.warn"] = "DiagnosticWarn",
  ["@diagnostic.info"] = "DiagnosticInfo",
  ["@diagnostic.hint"] = "DiagnosticHint",
}

function M.load()
  vim.cmd("hi clear")
  if vim.fn.exists("syntax_on") == 1 then
    vim.cmd("syntax reset")
  end
  vim.g.colors_name = M.name
  for group, attrs in pairs(M.highlights) do
    vim.api.nvim_set_hl(0, group, attrs)
  end
  for from, to in pairs(M.links) do
    vim.api.nvim_set_hl(0, from, { link = to })
  end
  for index, color in ipairs(M.palette.ansi) do
    vim.g["terminal_color_" .. (index - 1)] = color
  end
end

return M