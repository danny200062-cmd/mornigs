"""把社守 POS 價目表匯出檔（Tab 縮排格式）整理成點餐系統理解層用的菜單知識庫 JSON。

用法：python3 tools/build_menu_kb.py data/pos_menu_export_20260928.txt data/menu_kb.json
只取櫃台前台會用到的區塊：TAG-A1 / SALE-ONLINE（店內菜單）與 SALE-PACKAGE（套餐子品項）。
外送平台區塊（API-FP / API-UE）與其無選項的重複副本只記錄統計、不進知識庫。
"""
import json, sys, collections

def parse(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(lines) if l.startswith('###MENU###'))
    cats, cat, prod, grp = [], None, None, None
    for l in lines[start + 1:]:
        if not l.strip() or l.lstrip().startswith('#'):
            continue
        depth = len(l) - len(l.lstrip('\t'))
        f = l.rstrip('\n').split('\t')[depth:]
        if depth == 0:
            cat = {'name': f[0], 'status': f[1] if len(f) > 1 else '正常', 'products': []}
            cats.append(cat)
        elif depth == 1:
            prod = {'name': f[0], 'price': int(f[1]) if f[1].lstrip('-').isdigit() else f[1],
                    'desc': f[2] if len(f) > 2 else '', 'status': f[3] if len(f) > 3 else '正常',
                    'tag': f[4] if len(f) > 4 else '', 'groups': []}
            cat['products'].append(prod)
        elif depth == 2:
            grp = {'name': f[0], 'type': f[1] if len(f) > 1 else '單選', 'limit': f[2] if len(f) > 2 else '', 'options': []}
            prod['groups'].append(grp)
        elif depth == 3:
            if len(f) >= 4:
                grp['options'].append({'package': f[0], 'name': f[1], 'fee': int(f[2]), 'limit': f[3]})
            else:
                grp['options'].append({'name': f[0], 'fee': int(f[1]) if len(f) > 1 and f[1].lstrip('-').isdigit() else 0,
                                       'limit': f[2] if len(f) > 2 else ''})
    return cats

COUNTER_TAGS = {'TAG-A1', 'SALE-ONLINE', 'SALE-PACKAGE'}

def main(src, dst):
    cats = parse(src)
    kb = {'source': src, 'channels': {}, 'categories': []}
    seen_cat = collections.Counter()
    for c in cats:
        tags = {p['tag'] for p in c['products']}
        seen_cat[c['name']] += 1
        if tags <= COUNTER_TAGS and seen_cat[c['name']] == 1:
            kb['categories'].append(c)
        ch = ','.join(sorted(tags)) or '(無標籤副本)'
        kb['channels'].setdefault(ch, {'categories': 0, 'products': 0})
        kb['channels'][ch]['categories'] += 1
        kb['channels'][ch]['products'] += len(c['products'])
    # 統計
    prods = [p for c in kb['categories'] for p in c['products']]
    groups = [g for p in prods for g in p['groups']]
    kb['stats'] = {
        'categories': len(kb['categories']), 'products': len(prods),
        'products_on_sale': sum(1 for p in prods if p['status'] == '正常'),
        'option_groups': len(groups), 'options': sum(len(g['options']) for g in groups),
        'single_choice_groups': sum(1 for g in groups if g['type'] == '單選'),
        'group_name_freq': collections.Counter(g['name'] for g in groups).most_common(),
        'option_name_freq': collections.Counter(o['name'] for g in groups for o in g['options']).most_common(40),
    }
    json.dump(kb, open(dst, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in kb['stats'].items() if not k.endswith('_freq')}, ensure_ascii=False))
    print('channels', json.dumps(kb['channels'], ensure_ascii=False))
    print('group names', kb['stats']['group_name_freq'])
    print('single-choice groups by category:')
    print(collections.Counter((c['name'], g['name']) for c in kb['categories'] for p in c['products'] for g in p['groups'] if g['type'] == '單選'))

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
