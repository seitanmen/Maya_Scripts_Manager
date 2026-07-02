# -*- coding: utf-8 -*-
"""
Maya Scripts Manager  drag-and-drop installer / ドラッグ&ドロップ インストーラ

Usage / 使い方:
    Drag this file (DragAndDrop_Install.py) from the file browser onto the
    Maya viewport. / このファイルを Maya のビューポートへドラッグ&ドロップ
    するだけでインストールされます。

What it does / 動作:
    1. Resolves paths relative to this installer's location.
       このインストーラのある場所を基準にパスを決定します。
         <here>/DragAndDrop_Install.py          <- this file
         <here>/mayascriptsmanager.py            <- the tool
         <here>/repo/icons/mayascriptsmanager.png <- shelf icon
         <here>/repo/                            <- script list (JSON)
    2. Creates/updates <here>/.env (SCRIPT_REPO_PATH = <here>/repo),
       keeping other existing keys (e.g. LANG).
    3. Adds a shelf button that loads the tool from this location.

License: GPL-3.0 (see LICENSE)
"""

import os
import maya.cmds as cmds
import maya.mel as mel


# バイリンガル文言 / bilingual messages
_MSG = {
    "err_title":     {"ja": "インストールエラー", "en": "Install Error"},
    "err_notfound":  {"ja": "mayascriptsmanager.py が見つかりません:\n{}\n\n"
                            "このインストーラは mayascriptsmanager.py と同じ場所に置いてください。",
                      "en": "mayascriptsmanager.py was not found:\n{}\n\n"
                            "Place this installer in the same folder as mayascriptsmanager.py."},
    "done_title":    {"ja": "インストール完了", "en": "Install Complete"},
    "done_msg":      {"ja": "現在のシェルフ「{}」に Maya Scripts Manager を追加しました。\n"
                            "（古い/重複ボタンを {} 個削除）\n\n本体: {}\nリポジトリ(.env): {}",
                      "en": "Added Maya Scripts Manager to the current shelf \"{}\".\n"
                            "(removed {} old/duplicate button(s))\n\nTool: {}\nRepo (.env): {}"},
    "env_warn":      {"ja": "MayaScriptsManager: .env の書き込みに失敗: {}",
                      "en": "MayaScriptsManager: failed to write .env: {}"},
}


def _installerDir():
    """このインストーラが置かれているディレクトリ（スラッシュ区切り）"""
    return os.path.dirname(os.path.abspath(__file__)).replace("\\", "/")


def _readEnv(envPath):
    """既存 .env を KEY=VALUE 辞書で返す（無ければ空）"""
    env = {}
    if os.path.isfile(envPath):
        try:
            with open(envPath, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, _, v = s.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
        except Exception:
            pass
    return env


def _lang(baseDir):
    """言語判定: .env の LANG → Maya UI 言語 → 既定 en"""
    pref = _readEnv(baseDir + "/.env").get("LANG", "").strip().lower()
    if pref.startswith("ja"):
        return "ja"
    if pref.startswith("en"):
        return "en"
    try:
        ui = (cmds.about(uiLanguage=True) or "").lower()
    except Exception:
        ui = ""
    return "ja" if ui.startswith("ja") else "en"


def _msg(lang, key, *args):
    s = _MSG.get(key, {}).get(lang) or _MSG.get(key, {}).get("en") or key
    return s.format(*args) if args else s


def _writeEnv(baseDir, repoPath):
    """.env の SCRIPT_REPO_PATH を更新（他のキー/コメントは保持）"""
    envPath = baseDir + "/.env"
    newLine = "SCRIPT_REPO_PATH={}".format(repoPath.replace("/", "\\"))
    try:
        lines = []
        if os.path.isfile(envPath):
            with open(envPath, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        replaced = False
        for i, line in enumerate(lines):
            if line.strip().startswith("SCRIPT_REPO_PATH="):
                lines[i] = newLine
                replaced = True
                break
        if not replaced:
            if not lines:
                lines = ["# Maya Scripts Manager settings / 設定"]
            lines.append(newLine)
        with open(envPath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return envPath
    except Exception as e:
        cmds.warning(_msg(_lang(baseDir), "env_warn", e))
        return None


def _removeExistingButtons():
    """全シェルフから本ツールの旧/新ボタンを削除（掃除+重複防止）。戻り値: 削除数"""
    removed = 0
    try:
        g = mel.eval("$tmp = $gShelfTopLevel")
        shelves = cmds.tabLayout(g, query=True, childArray=True) or []
    except Exception:
        return removed
    for shelf in shelves:
        try:
            buttons = cmds.shelfLayout(shelf, query=True, childArray=True) or []
        except Exception:
            continue
        for btn in buttons:
            try:
                if cmds.objectTypeUI(btn) != "shelfButton":
                    continue
                cmd = cmds.shelfButton(btn, query=True, command=True) or ""
                lbl = cmds.shelfButton(btn, query=True, label=True) or ""
            except Exception:
                continue
            low = cmd.lower()
            if ("vmtscriptmanager" in low or "mayascriptsmanager" in low
                    or lbl in ("VMTScriptManager", "MayaScriptsManager")):
                try:
                    cmds.deleteUI(btn)
                    removed += 1
                except Exception:
                    pass
    return removed


def install():
    baseDir = _installerDir()
    lang = _lang(baseDir)
    managerPath = baseDir + "/mayascriptsmanager.py"
    iconPath = baseDir + "/repo/icons/mayascriptsmanager.png"
    repoPath = baseDir + "/repo"

    # 本体の存在チェック / tool existence check
    if not os.path.isfile(managerPath):
        cmds.confirmDialog(title=_msg(lang, "err_title"),
                           message=_msg(lang, "err_notfound", managerPath))
        return

    # 1) .env を更新（既存キー保持） / update .env (keep other keys)
    _writeEnv(baseDir, repoPath)

    # 2) シェルフボタンのコマンド（本体を読み込んで起動）
    #    __file__ を渡すことでアイコン/.env の相対解決を有効化
    command = "\n".join([
        "script_path = r'%s'" % managerPath,
        "with open(script_path, encoding='utf-8') as f:",
        "    exec(f.read(), {'__file__': script_path})",
    ])

    # アイコン（無ければ Maya 既定アイコン）
    icon = iconPath if os.path.isfile(iconPath) else "commandButton.png"

    # 3) 旧/重複ボタンを掃除してから、現在のシェルフタブに追加
    removed = _removeExistingButtons()

    gShelfTopLevel = mel.eval("$tmp = $gShelfTopLevel")
    currentShelf = cmds.tabLayout(gShelfTopLevel, query=True, selectTab=True)

    cmds.shelfButton(
        parent=currentShelf,
        label="MayaScriptsManager",
        annotation="Maya Scripts Manager",
        image=icon,
        image1=icon,
        command=command,
        sourceType="python"
    )

    # 次回起動でも残るようシェルフを保存
    try:
        mel.eval("saveAllShelves $gShelfTopLevel")
    except Exception:
        pass

    cmds.confirmDialog(title=_msg(lang, "done_title"),
                       message=_msg(lang, "done_msg", currentShelf, removed, managerPath, repoPath))


def onMayaDroppedPythonFile(*args):
    """Maya のビューポートへドラッグ&ドロップされたときに呼ばれる"""
    install()
