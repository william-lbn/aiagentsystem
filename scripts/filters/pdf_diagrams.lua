-- Keep SVG for HTML/EPUB, but use the Graphviz-generated vector PDF for
-- LaTeX/PDF so the publication path does not depend on rsvg-convert.
--
-- The compatibility publisher is an explicit two-stage pipeline:
--   Pandoc -> .build/latex/*.tex -> XeLaTeX (cwd = repository root)
-- Therefore use a repository-relative path.  Absolute checkout paths would
-- leak into XDV/PDF inputs and break byte-identical clean rebuilds.
function Image(img)
  if FORMAT:match("latex") or FORMAT:match("pdf") then
    local src = img.src
    if src:match("assets/diagrams/[^/]+%.svg$") then
      local pdf = src:gsub("assets/diagrams/([^/]+)%.svg$", "assets/diagrams/pdf/%1.pdf")
      -- A Quarto Book invokes Pandoc with chapter paths already rebased to the
      -- project root (for example
      -- ``book/zh/chapters/../../assets/...``).  The compatibility publisher
      -- feeds the assembled ``book/zh/book.md`` instead, where the same image
      -- is ``assets/...`` and still needs the repository-level ``book/``
      -- prefix.  Prefix only that second form; doing it unconditionally creates
      -- the invalid Quarto path ``book/book/...``.
      if src:match("^book/") then
        img.src = pdf
      else
        img.src = "book/" .. pdf
      end
    end
  end
  return img
end
