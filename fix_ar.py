"""修复 GPT 页面账号 ID 行样式：统一用 display:flex"""
import os, glob

templates = r'd:\bedrock-inference-profiles\templates'
gpt_files = glob.glob(os.path.join(templates, 'gpt_*.html'))

for f in gpt_files:
    with open(f, 'r', encoding='utf-8') as fh:
        c = fh.read()
    c2 = c

    # 1. 账号 ID 行：style="display:none" → 统一，出现时改为 flex
    #    JS 里 $("ar").style.display="" 改为 $("ar").style.display="flex"
    c2 = c2.replace('$("ar").style.display=""', '$("ar").style.display="flex"')
    c2 = c2.replace("$('ar').style.display=\"\"", "$('ar').style.display=\"flex\"")

    # 2. ar 区域加上 flex 布局样式（与 Claude 一致）
    # Claude 的 #ar 有 padding, background, border, border-radius
    old_ar_style = '<div class="fr" id="ar" style="display:none">'
    new_ar_style = '<div id="ar" style="display:none;margin-top:2px;padding:8px 10px;background:var(--ok-bg);border:1px solid var(--ok-bd);border-radius:var(--r-sm)">'
    c2 = c2.replace(old_ar_style, new_ar_style)

    # 3. 账号 ID span 加上 monospace 样式
    old_aid = '<span id="aid" style="font-family:monospace;font-weight:600"></span>'
    new_aid = '<span id="aid" style="font-weight:600;font-size:12px;font-family:\'SF Mono\',Consolas,monospace"></span>'
    c2 = c2.replace(old_aid, new_aid)

    if c2 != c:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(c2)
        print(f'UPDATED: {os.path.basename(f)}')
    else:
        print(f'skip: {os.path.basename(f)}')
