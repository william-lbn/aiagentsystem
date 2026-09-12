-- PDF-only semantic bridge for the Pandoc compatibility path.
-- It maps generated structural markers to native LaTeX book commands.
-- Markdown interpretation remains Pandoc/Quarto's responsibility.

local stringify = pandoc.utils.stringify
local in_appendices = false

local function has_class(el, wanted)
  for _, c in ipairs(el.classes or {}) do
    if c == wanted then return true end
  end
  return false
end

local function latex_inline(inlines)
  local doc = pandoc.Pandoc({pandoc.Plain(inlines)})
  local s = pandoc.write(doc, 'latex')
  return (s:gsub('%s+$', ''))
end

local function strip_appendix_prefix(text)
  local out = text:gsub('^附录%s+[A-Z]%s*:%s*', '')
  out = out:gsub('^附录%s+[A-Z]%s*：%s*', '')
  return out
end

local function without_class(classes, unwanted)
  local out = {}
  for _, c in ipairs(classes or {}) do
    if c ~= unwanted then table.insert(out, c) end
  end
  return out
end

function Header(el)
  if not FORMAT:match('latex') then return nil end

  if has_class(el, 'part') then
    return pandoc.RawBlock('latex', '\\part{' .. latex_inline(el.content) .. '}')
  end

  if has_class(el, 'appendices-start') then
    in_appendices = true
    return pandoc.RawBlock('latex',
      '\\appendix\n\\part*{附录}\n\\addcontentsline{toc}{part}{附录}')
  end

  if (in_appendices or has_class(el, 'appendix-title')) and el.level == 1 then
    local clean = strip_appendix_prefix(stringify(el.content))
    local classes = without_class(el.classes, 'unnumbered')
    return pandoc.Header(el.level, {pandoc.Str(clean)}, {el.identifier, classes, el.attributes})
  end

  return nil
end
