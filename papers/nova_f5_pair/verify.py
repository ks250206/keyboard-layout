#!/usr/bin/env python3
"""Check manuscript inputs, complete KLA tables, and four exported documents."""
from pathlib import Path
import hashlib, json, re, subprocess
from docx import Document
import build

HERE=Path(__file__).resolve().parent

def main():
    bundle,lookup=build.checked_inputs()
    for lang in ('ja','en'):
        tables=build.make_tables(lang,bundle,lookup)
        assert sum(len(tables[k]['rows'])*(len(tables[k]['headers'])-1) for k in ('kla_all','kla_jp_domains','kla_code_all'))==420
        doc=Document(HERE/f'nova_f5_pair_{lang}.docx')
        assert doc.core_properties.author == build.AUTHOR == 'ks250206'
        assert doc.core_properties.last_modified_by == build.AUTHOR
        assert len(doc.tables)==12,len(doc.tables)
        text='\n'.join(p.text for p in doc.paragraphs)
        assert 'F5-Pair' in text and '94' in text and '142' in text
        assert '{{' not in text and '[[PAGEBREAK]]' not in text
        assert len(doc.inline_shapes)==2
        pdf=HERE/f'nova_f5_pair_{lang}.pdf'
        assert pdf.stat().st_size>100000
        info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
        pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
        assert 10<=pages<=20,(lang,pages)
        content=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
        assert '{{' not in content and '\ufffd' not in content and '[[PAGEBREAK]]' not in content
        assert '72.93' in content and '62.00' in content
        print(f'PASS {lang}: {pages} pages, 12 tables, 2 figures, 420 appendix KLA values')
    manifest=json.loads((HERE/'build_manifest.json').read_text())
    for name,expected in manifest['outputs'].items():
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected,name
    print('PASS: source hashes and all four output hashes')

if __name__=='__main__':main()
