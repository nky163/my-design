# デザインルール再構築 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4つの部品カタログ文書を、1つの制約仕様 `design-rule/rules.html` に置き換え、Claude がその場で部品と図を生成できるようにする。

**Architecture:** 文書を2ゾーンに割る。固定ゾーン（トークン・骨格・影・キー送り）は丸ごとコピーする CSS ブロックとして提示し、自由ゾーン（部品・図）は制約だけを書く。LT登壇と読解メモの差は1つのモード表に閉じ込める。検証は、書き直さない実物4デッキに対する機械チェックで行う。

**Tech Stack:** 素の HTML + CSS（ビルドなし）、検証は Python 3 標準ライブラリのみ（`re`）。ブラウザで直接開く前提。

**Spec:** `docs/superpowers/specs/2026-09-02-design-rules-simplification-design.md`

## Global Constraints

- 色は11トークンのみ: `--surround:#171410` `--paper:#F8F6F2` `--card:#FFFFFF` `--ink:#26333F` `--ink-2:#4E5F60` `--ink-3:#8B98A4` `--line:#E6E1D9` `--fill:#F1ECE4` `--accent:#D9822B` `--neg:#DC4A4A` `--pos:#12776A`
- パレット外の色を作らない。淡い面は `rgba(<トークンの値>, α)` で書く
- タイプスケールは5段のみ: `0.8cqw` / `1.2cqw` / `1.8cqw` / `2.8cqw` / `5.2cqw`
- 書体は `"Lato","Zen Kaku Gothic New","Noto Sans JP",sans-serif` の順
- `.reveal` は `.55s` / `calc(var(--i,0) * .12s)`
- `.slide` の横 padding は `5.2cqw` 固定
- 影は2段のみ: 弱 `0 .12cqw .8cqw rgba(38,51,63,.06)` / 強 `0 .2cqw 1cqw rgba(38,51,63,.14)`。`drop-shadow` は使わない
- 単位は `cqw` / `cqh` のみ。`rem` と `px` をレイアウトに混ぜない
- **`memo/` `agentic-qa/` `sdlc-vibe-coding/` `newrelic-ai-coding-2026/` は git 未追跡。読むだけ。絶対に変更・削除しない**
- 作業ブランチは `redesign-rules`

---

## File Structure

| ファイル | 責務 |
|---|---|
| `tools/check-rules.py` | 制約を機械チェックする検証スクリプト。実物4デッキと新 sample の両方に当てる |
| `design-rule/rules.html` | 制約仕様（正本）。6章、部品クラスを定義しない |
| `design-rule/sample.html` | 見本デッキ。ルールを、ルール自身の型で説明する |
| `paper-rule/` | → `git mv` で `design-rule/` に改名 |
| `dojo-rule/` `ledger-rule/` `theorem-rule/` | 削除 |

---

## Task 1: 検証スクリプトを作る

先に検証を作る。この時点では新ルール文書がないので、実物4デッキに当てて
「今どのルールが実際に守られているか」のベースラインを取る。

**Files:**
- Create: `tools/check-rules.py`

**Interfaces:**
- Produces: `python3 tools/check-rules.py <html...>` — ファイルごとに違反を出力し、
  違反があれば exit 1。Task 3・4 がこれを合格条件に使う。

- [ ] **Step 1: 検証スクリプトを書く**

```python
#!/usr/bin/env python3
"""デザインルールの機械チェック。

使い方: python3 tools/check-rules.py design-rule/sample.html
        python3 tools/check-rules.py --baseline memo/sample.html ...

--baseline は違反を報告するが exit 0 で終わる（実物デッキの現状把握用）。
"""
import re
import sys

TOKENS = {
    "--surround": "#171410", "--paper": "#F8F6F2", "--card": "#FFFFFF",
    "--ink": "#26333F", "--ink-2": "#4E5F60", "--ink-3": "#8B98A4",
    "--line": "#E6E1D9", "--fill": "#F1ECE4", "--accent": "#D9822B",
    "--neg": "#DC4A4A", "--pos": "#12776A",
}
PALETTE = {v.upper() for v in TOKENS.values()}
SCALE = {"0.8", ".8", "1.2", "1.8", "2.8", "5.2"}


def check_palette(src):
    """パレット外の生 hex 値を拾う。"""
    bad = sorted({h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", src)} - PALETTE)
    return [f"パレット外の色: {h}" for h in bad]


def check_scale(src):
    """font-size / font: 短縮形の cqw 値が5段に収まっているか。"""
    sizes = set()
    for decl in re.findall(r"font(?:-size)?\s*:\s*[^;{}]*", src):
        for m in re.findall(r"(\d*\.?\d+)cqw", decl):
            sizes.add(m.rstrip("0").rstrip(".") if "." in m else m)
    bad = sorted(s for s in sizes if s not in SCALE and s.lstrip("0") not in SCALE)
    return [f"タイプスケール外の文字サイズ: {s}cqw" for s in bad]


def check_shadow(src):
    """影は2段のみ、drop-shadow は禁止。"""
    out = []
    if "drop-shadow" in src:
        out.append("drop-shadow は使わない（box-shadow の2段のみ）")
    allowed = {
        "0 .12cqw .8cqw rgba(38,51,63,.06)",
        "0 .2cqw 1cqw rgba(38,51,63,.14)",
    }
    for v in re.findall(r"box-shadow\s*:\s*([^;{}]+)", src):
        norm = " ".join(v.split()).rstrip()
        if norm not in allowed:
            out.append(f"規定外の影: {norm}")
    return out


def check_skeleton(src):
    """固定ゾーンがそのままコピーされているか。"""
    out = []
    checks = [
        (r"container-type\s*:\s*size", "`.deck` に container-type:size がない"),
        (r"width\s*:\s*min\(100vw,\s*177\.78vh\)", "16:9 の .deck 幅指定がない"),
        (r"padding\s*:\s*[\d.]+cqw\s+5\.2cqw", ".slide の横 padding が 5.2cqw でない"),
        (r"animation:\s*revealIn\s+\.55s", ".reveal が .55s でない"),
        (r"var\(--i,\s*0\)\s*\*\s*\.12s", ".reveal の遅延が .12s でない"),
    ]
    for pattern, msg in checks:
        if not re.search(pattern, src):
            out.append(msg)
    return out


def check_units(src):
    """レイアウトに px を混ぜていないか（線幅 1px と 999px の丸めは許す）。"""
    bad = set()
    for m in re.findall(r"(?:padding|margin|gap|width|height|top|left|right|bottom)\s*:\s*[^;{}]*?(\d*\.?\d+)px", src):
        if m not in {"1", "999"}:
            bad.add(m)
    return [f"レイアウトに px: {v}px（cqw を使う）" for v in sorted(bad)]


CHECKS = [check_palette, check_scale, check_shadow, check_skeleton, check_units]


def main(argv):
    baseline = "--baseline" in argv
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if not paths:
        print("使い方: check-rules.py [--baseline] <html...>", file=sys.stderr)
        return 2

    total = 0
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        problems = [p for check in CHECKS for p in check(src)]
        total += len(problems)
        mark = "OK" if not problems else f"{len(problems)}件"
        print(f"\n=== {path} — {mark} ===")
        for p in problems:
            print(f"  - {p}")

    print(f"\n合計 {total} 件")
    return 0 if (baseline or total == 0) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 2: 実物4デッキでベースラインを取り、スクリプトが動くことを確認**

```bash
python3 tools/check-rules.py --baseline \
  memo/sample.html agentic-qa/sample.html \
  sdlc-vibe-coding/sample.html newrelic-ai-coding-2026/sample.html
```

期待: exit 0。各デッキに違反が並ぶ（タイプスケール違反が多数出るはず＝spec D3a の新制約なので当然）。
**ここで骨格チェック（`check_skeleton`）が4デッキとも0件でなければスクリプトのバグ**なので直す。
骨格は実測で不変が確認済みだから、実物は必ず通る。

- [ ] **Step 3: まだ存在しない `design-rule/sample.html` に当てて落ちることを確認**

```bash
python3 tools/check-rules.py design-rule/sample.html; echo "exit=$?"
```

期待: `FileNotFoundError` で落ちる。これが Task 3 で埋める失敗。

- [ ] **Step 4: コミット**

```bash
git add tools/check-rules.py
git commit -m "デザインルールの検証スクリプトを追加

実物4デッキに当ててベースラインを取れる。骨格・パレット・タイプスケール・
影・単位の5項目を機械チェックする。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VRij3raBKHEp1Th774gP62"
```

---

## Task 2: フォルダを整理する

**Files:**
- Rename: `paper-rule/` → `design-rule/`
- Delete: `dojo-rule/` `ledger-rule/` `theorem-rule/`

- [ ] **Step 1: 未追跡フォルダが巻き込まれないことを確認**

```bash
git status --short | grep '^??'
```

期待: `memo/` は出ない（追跡済み）。`agentic-qa/` `sdlc-vibe-coding/`
`newrelic-ai-coding-2026/` `2026 Agentic Coding Trends Report.pdf` が `??` で出る。
**この4つは以降のコマンドで一切触らない。**

- [ ] **Step 2: 改名する**

```bash
git mv paper-rule design-rule
```

- [ ] **Step 3: 3フォルダを削除する**

```bash
git rm -r --quiet dojo-rule ledger-rule theorem-rule
```

- [ ] **Step 4: 未追跡フォルダが無傷であることを確認**

```bash
ls -d agentic-qa sdlc-vibe-coding newrelic-ai-coding-2026 memo design-rule
ls -d dojo-rule ledger-rule theorem-rule 2>&1 | tail -1
```

期待: 前者は5つとも存在。後者は "No such file or directory"。

- [ ] **Step 5: コミット**

```bash
git add -A
git commit -m "ルール文書を1つに集約

paper-rule を design-rule に改名し、dojo/ledger/theorem を削除。
統合後の文書は LT登壇と読解メモの両方を扱うため paper という名前が合わない。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VRij3raBKHEp1Th774gP62"
```

---

## Task 3: 見本デッキを作る

ルール文書より先に見本を作る。見本が検証を通ることが、ルールが書けることの証明になる。

**Files:**
- Rewrite: `design-rule/sample.html`

**Interfaces:**
- Consumes: `tools/check-rules.py`（Task 1）
- Produces: 固定ゾーンの正準 CSS。Task 4 の `rules.html` はこれを逐語で引用する。

- [ ] **Step 1: 固定ゾーンの CSS を確定させる**

これが `rules.html` に「丸ごとコピーする」として載る唯一のブロック。

```css
:root{
  --surround:#171410; --paper:#F8F6F2; --card:#FFFFFF;
  --ink:#26333F; --ink-2:#4E5F60; --ink-3:#8B98A4;
  --line:#E6E1D9; --fill:#F1ECE4;
  --accent:#D9822B; --neg:#DC4A4A; --pos:#12776A;
}
*{ box-sizing:border-box; }
body{
  margin:0; background:var(--surround); color:var(--ink);
  font-family:"Lato","Zen Kaku Gothic New","Noto Sans JP",sans-serif;
  display:flex; align-items:center; justify-content:center; min-height:100vh;
}
.deck{
  position:relative;
  width:min(100vw, 177.78vh); height:min(56.25vw, 100vh);
  container-type:size; overflow:hidden;
  background:var(--paper);
  outline:none;
}
.slide{ position:absolute; inset:0; display:none; flex-direction:column; padding:4.4cqw 5.2cqw 6cqw; }
.slide.is-active{ display:flex; }
.deckfoot{ position:absolute; right:5.2cqw; bottom:2.2cqw; font:400 .8cqw "Lato",sans-serif; color:var(--ink-3); font-variant-numeric:tabular-nums; }
.footlogo{ position:absolute; left:5.2cqw; bottom:2.2cqw; display:flex; align-items:center; gap:.5cqw; max-width:70%; }
.reveal{ opacity:0; transform:translateY(.6cqw); animation:revealIn .55s cubic-bezier(.2,.7,.3,1) forwards; animation-delay:calc(var(--i,0) * .12s); }
@keyframes revealIn{ to{ opacity:1; transform:none; } }
@media (prefers-reduced-motion:reduce){ .reveal{ animation:none; opacity:1; transform:none; } }
```

`.footlogo` に色とサイズを書かないのが今回の変更点。モードごとに指定する（spec D4）。

- [ ] **Step 2: キー送りスクリプトを確定させる**

```html
<script>
(function(){
  var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var i = 0;
  var deck = document.getElementById('deck');
  function render(){
    slides.forEach(function(s, idx){ s.classList.toggle('is-active', idx === i); });
  }
  function go(d){
    var n = i + d;
    if(n < 0 || n >= slides.length) return;
    i = n; render();
  }
  window.addEventListener('keydown', function(e){
    if(e.key === 'ArrowRight' || e.key === ' '){ go(1); e.preventDefault(); }
    if(e.key === 'ArrowLeft'){ go(-1); e.preventDefault(); }
  });
  deck.setAttribute('tabindex', '0');
  render();
})();
</script>
```

- [ ] **Step 3: 見本デッキの中身を書く（13枚）**

各枚が、そのページで説明しているルール自身で組まれていること。
部品はこの見本のためにその場で作る（＝自由ゾーンの実演）。
文字サイズは5段（`.8` / `1.2` / `1.8` / `2.8` / `5.2` cqw）のみ。

| # | 内容 | モード |
|---|---|---|
| 1 | 表紙「デザインルール」 | LT |
| 2 | 2つのモード（比較表） | LT |
| 3 | 2つのゾーン：固定と自由 | LT |
| 4 | 固定ゾーンの骨格（コード） | LT |
| 5 | 色：11トークンの見本 | LT |
| 6 | 色：accent は1枚1役 | LT |
| 7 | 文字：5段スケール | LT |
| 8 | 1枚の作り方（LTモードの実演） | LT |
| 9 | 1枚の作り方（読解メモモードの実演） | 読解メモ |
| 10 | 影は2段だけ | LT |
| 11 | 図：色は透過で作る | LT |
| 12 | 図：説明文は figcaption へ | LT |
| 13 | 締め | LT |

9枚目だけ `.slide` に `style="padding:3.6cqw 5.2cqw 5.2cqw"` を当て、
`.footlogo` を `400 .8cqw` / `--ink-3` にして原典URLを置く。
他は `.footlogo` を `800 .8cqw` / `--ink` にしてデッキ名を置く。
モード差はサイズではなく**太さと色**で出す（サイズは両モードとも XS = `.8cqw`）。

- [ ] **Step 4: 検証を通す**

```bash
python3 tools/check-rules.py design-rule/sample.html
```

期待: `合計 0 件`、exit 0。
違反が出たら**ルールではなく見本を直す**。見本がルールを満たせないなら、
そのルールは実行不可能なので Task 4 に進む前に spec に戻って相談する。

- [ ] **Step 5: ブラウザで開いて目視確認**

```bash
open design-rule/sample.html
```

確認: 16:9 が中央に出る／矢印キーで送れる／13枚とも文字がはみ出していない／
9枚目だけ余白と footlogo が違う。

- [ ] **Step 6: コミット**

```bash
git add design-rule/sample.html
git commit -m "見本デッキを制約仕様の形に作り直す

部品カタログを使わず、各ページをその場で組んだ部品で構成。
5段スケール・11トークン・影2段の制約内で検証を通る。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VRij3raBKHEp1Th774gP62"
```

---

## Task 4: ルール文書を書く

**Files:**
- Rewrite: `design-rule/rules.html`

**Interfaces:**
- Consumes: Task 3 で確定した固定ゾーン CSS とキー送りスクリプト（逐語で引用する）

- [ ] **Step 1: 6章の中身を書く**

```
01 何のための型か      2つのモード表（spec D4）。1枚で言い切れないなら2枚に割る
02 そのままコピーする骨格  Task 3 Step 1・2 のコードを逐語で。「変えない」と明記
03 色                  11トークン表（役割つき）。accent は1枚1役。
                       neg/pos は Before/After 専用。淡い面は rgba で作る
04 文字                2書体の指定順。5段スケール表（LT / 読解メモの役割つき）。
                       「20〜33種類使われていたので5段に絞った」経緯を1行
05 1枚の作り方          情報量の上限（モード別）／余白 5.2cqw ／影は2段だけ／
                       単位は cqw のみ
06 図                  4行の制約（色・div でも SVG でもよい・説明文は外・線は2種）
```

- [ ] **Step 2: 部品クラスを1つも定義していないことを確認**

```bash
grep -oE '^\s*\.[a-zA-Z][a-zA-Z0-9_-]*\s*\{' design-rule/rules.html \
  | grep -oE '\.[a-zA-Z0-9_-]+' | sort -u
```

期待: 文書自身の presentation 用クラス（`.wrap` `.head` 等）と、
02章に引用した骨格6クラス（`.deck` `.slide` `.slide.is-active` `.deckfoot`
`.footlogo` `.reveal`）のみ。`.pcard` `.steps` `.bar` `.spectrum` 等が
1つでも出たら削る。

- [ ] **Step 3: 実在しないファイルへの参照がないことを確認**

```bash
grep -n 'CLAUDE\.md\|index\.html' design-rule/rules.html
```

期待: 何も出ない（現行 §10 の虚偽記載を持ち込んでいないこと）。

- [ ] **Step 4: 行数の目標を確認**

```bash
total=$(wc -l < design-rule/rules.html)
css=$(sed -n '/<style>/,/<\/style>/p' design-rule/rules.html | wc -l)
echo "全体 $total 行 / presentation CSS $css 行 / 本文 $((total - css)) 行"
```

期待: 本文が約130行（現行298行）。大きく超えるなら書きすぎ。

- [ ] **Step 5: コミット**

```bash
git add design-rule/rules.html
git commit -m "ルール文書を制約仕様に書き直す

10章の部品カタログを6章の制約仕様に。部品クラスを1つも定義せず、
固定ゾーンのコピー用 CSS と自由ゾーンの制約だけを載せる。
実在しない CLAUDE.md / index.html への参照を削除。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VRij3raBKHEp1Th774gP62"
```

---

## Task 5: 実物デッキに当てて検証する

spec の検証節を実行する。**自己採点を避けるため、書き直していない4デッキを使う。**

**Files:**
- Modify: `design-rule/rules.html`（検証で見つかった抜け漏れの反映）

- [ ] **Step 1: 実物4デッキから各3枚を取り、ルールを1つずつ当てる**

```bash
for d in memo agentic-qa sdlc-vibe-coding newrelic-ai-coding-2026; do
  echo "=== $d ==="
  awk '/<section class="slide/{n++} n>=2 && n<=4' $d/sample.html | head -80
done
```

6章の各ルールについて、この12枚が満たすかを目で確認し、下表を埋める。

| ルール | 満たす枚数 | 判定 |
|---|---|---|
| 骨格をそのまま使っている | /12 | |
| 色が11トークンとその透過値のみ | /12 | |
| 影が2段のみ | /12 | |
| 図の説明文が figcaption か本文にある | /12 | |
| 図の線が2種以内 | /12 | |
| 読解メモは出典を持つ | /12 | |

- [ ] **Step 2: 0件のルールを処理する**

どの実物も満たさないルールが出たら、次のどちらかにする。両方とも記録を残す。

- **削る** — 実態に反するルールだった（例: 現行の「図はSVGで描く」）
- **残す** — 意図的な新制約。`rules.html` に「★これは新しく課す制約」と明記し、
  ユーザーに承認を取る

**勝手に残さない。**5段スケールは spec D3a で承認済みなので、これには当たらない。

- [ ] **Step 3: 3〜4デッキが共通でやっているのに書かれていないことを探す**

Step 1 の12枚を見て、ルールに無い共通パターンがあれば抜け漏れとして 06章か05章に足す。

- [ ] **Step 4: 検証結果を文書末尾に書く**

`rules.html` の末尾に、Step 1 の表と Step 2 の判断を「このルールは何で検証したか」
として残す。現行の「写真13枚から再構成、\*印は推定」という出所不明の注記を置き換える。

- [ ] **Step 5: 全ファイルで検証スクリプトを流す**

```bash
python3 tools/check-rules.py design-rule/sample.html
python3 tools/check-rules.py --baseline \
  memo/sample.html agentic-qa/sample.html \
  sdlc-vibe-coding/sample.html newrelic-ai-coding-2026/sample.html
```

期待: 前者が `合計 0 件` で exit 0。後者はベースラインなので違反が出てよいが、
**骨格チェックは4デッキとも0件**であること（Task 1 Step 2 と同じ）。

- [ ] **Step 6: コミット**

```bash
git add design-rule/rules.html
git commit -m "実物デッキ12枚でルールを検証し、結果を文書に記録

書き直していない4デッキから各3枚を取り、6章の各ルールを照合。
出所不明だった注記を、検証可能な根拠に置き換えた。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01VRij3raBKHEp1Th774gP62"
```

---

## Task 6: 完了条件を確認する

**Files:** なし（確認のみ）

- [ ] **Step 1: spec の完了条件を1行ずつ測る**

```bash
cd /Users/nakayahiromi/workspace/my-design
total=$(wc -l < design-rule/rules.html)
css=$(sed -n '/<style>/,/<\/style>/p' design-rule/rules.html | wc -l)
echo "rules.html 本文: $((total - css)) 行（目標 約130 / 現行 298）"
echo "rules.html 全体: $total 行（目標 約260 / 現行 506）"
echo "ルール文書の数: $(ls -d *-rule 2>/dev/null | wc -l)（目標 1）"
echo "章の数: $(grep -c 'class="head"' design-rule/rules.html)（目標 6）"
echo "消えたフォルダ: $(ls -d dojo-rule ledger-rule theorem-rule 2>/dev/null | wc -l) 残（目標 0）"
echo "未追跡フォルダ: $(ls -d agentic-qa sdlc-vibe-coding newrelic-ai-coding-2026 2>/dev/null | wc -l) 残（目標 3）"
```

- [ ] **Step 2: 部品クラス定義が0であることを再確認**

```bash
grep -oE '\.(pcard|steps|bar|quote|highlight|cclose|stats|refbox|figrow|figcard|rightUI|spectrum|loop|archdiagram|nest|distchart|netdiagram|formula-block|kpi-grid|risk-table|compare-card|step-cards|digest|beat|chiprow)\b' design-rule/rules.html | sort -u
```

期待: 何も出ない。

- [ ] **Step 3: 結果を報告する**

上の数値をそのまま報告する。目標に届かない項目があれば、
達成したことにせず、届かなかった項目と理由を明示する。
