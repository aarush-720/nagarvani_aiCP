import subprocess, json, re, sys
pdf = sys.argv[1]; heads = json.load(open(sys.argv[2]))
n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
texts = [subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", pdf, "-"], capture_output=True, text=True).stdout for i in range(1, n + 1)]
norm = lambda s: re.sub(r"\s+", " ", s)
start = next(i for i, t in enumerate(texts) if "Chapter 1 Introduction" in norm(t) and "Indian urban local bodies" in t)
pages = {}
for lvl, h in heads:
    key = norm(h)
    for i in range(start, n):
        if key in norm(texts[i]): pages[h] = i - start + 1; break
json.dump(pages, open("pages.json", "w"), ensure_ascii=False, indent=0)
print(len(pages), "of", len(heads), "found; missing:", [h for _, h in heads if h not in pages])
