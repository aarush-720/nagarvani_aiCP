set -e
cd "$(dirname "$0")"
SOFF=$(ls /root/.claude/skills/synced/*/docx/scripts/office/soffice.py | head -1)
rm -f pages.json
node report.js report.docx >/dev/null
python3 $SOFF --headless --convert-to pdf report.docx >/dev/null 2>&1
python3 paginate.py report.pdf heads.json
node report.js report.docx >/dev/null
python3 $SOFF --headless --convert-to pdf report.docx >/dev/null 2>&1
python3 paginate.py report.pdf heads.json
node report.js report.docx >/dev/null
python3 $SOFF --headless --convert-to pdf report.docx >/dev/null 2>&1
pdfinfo report.pdf | grep Pages
