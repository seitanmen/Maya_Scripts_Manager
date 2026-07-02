# -*- coding: utf-8 -*-
#
# Maya Scripts Manager
# Copyright (C) 2026 seitanmen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version. See the LICENSE file or
# <https://www.gnu.org/licenses/> for details.
#
import maya.cmds as cmds
import maya.mel as mel
import json
import os
from functools import partial


# ---------------------------------------------------------------------------
# 多言語対応（i18n） / Localization
#   言語は .env の LANG（"ja" / "en"）→ 無ければ Maya の UI 言語で自動判定。
#   Language: .env LANG ("ja"/"en"), else auto-detect from Maya UI language.
# ---------------------------------------------------------------------------
STRINGS = {
    "name_label":        {"ja": "スクリプト名:",                 "en": "Script Name:"},
    "desc_label":        {"ja": "詳細説明:",                     "en": "Description:"},
    "type_label":        {"ja": "スクリプトタイプ:",             "en": "Script Type:"},
    "tab_script":        {"ja": "スクリプト",                     "en": "Script"},
    "tab_dc":            {"ja": "ダブルクリック（任意）",         "en": "Double-click (optional)"},
    "browse_icon":       {"ja": "アイコンを参照",                 "en": "Browse Icon"},
    "register_btn":      {"ja": "スクリプトを登録",               "en": "Register Script"},
    "list_label":        {"ja": "スクリプトリスト:",             "en": "Script List:"},
    "export_btn":        {"ja": "リストの書き出し",               "en": "Export List"},
    "import_btn":        {"ja": "リストの読み込み",               "en": "Import List"},
    "run_btn":           {"ja": "選択したスクリプトを実行",       "en": "Run Selected"},
    "delete_btn":        {"ja": "選択したスクリプトを削除",       "en": "Delete Selected"},
    "tab_register":      {"ja": "登録 / 編集",                    "en": "Register / Edit"},
    "tab_list":          {"ja": "スクリプトリスト",               "en": "Script List"},

    "err_title":         {"ja": "エラー",                         "en": "Error"},
    "err_name_content":  {"ja": "スクリプト名と内容を入力してください。",
                          "en": "Please enter a script name and content."},
    "err_select_script": {"ja": "スクリプトを選択してください。",
                          "en": "Please select a script."},
    "err_select_delete": {"ja": "削除するスクリプトを選択してください。",
                          "en": "Please select a script to delete."},

    "scripttype_title":  {"ja": "スクリプトタイプ",               "en": "Script Type"},
    "scripttype_msg":    {"ja": "スクリプトタイプを選択してください:",
                          "en": "Select the script type:"},
    "btn_cancel":        {"ja": "キャンセル",                     "en": "Cancel"},

    "save_err_title":    {"ja": "保存エラー",                     "en": "Save Error"},
    "save_err_msg":      {"ja": "スクリプトの保存エラー: {}",     "en": "Failed to save scripts: {}"},
    "load_err_title":    {"ja": "読み込みエラー",                 "en": "Load Error"},
    "load_err_msg":      {"ja": "スクリプトの読み込みエラー: {}", "en": "Failed to load scripts: {}"},

    "export_ok_title":   {"ja": "書き出し成功",                   "en": "Export Complete"},
    "export_ok_msg":     {"ja": "{} にスクリプトを書き出しました。",
                          "en": "Scripts exported to {}."},
    "export_err_title":  {"ja": "書き出しエラー",                 "en": "Export Error"},
    "export_err_msg":    {"ja": "スクリプトの書き出しエラー: {}",
                          "en": "Failed to export scripts: {}"},

    "import_ok_title":   {"ja": "インポート成功",                 "en": "Import Complete"},
    "import_ok_msg":     {"ja": "{} からスクリプトをインポートしました。",
                          "en": "Scripts imported from {}."},
    "import_err_title":  {"ja": "インポートエラー",               "en": "Import Error"},
    "import_err_msg":    {"ja": "スクリプトの読み込みエラー: {}",
                          "en": "Failed to import scripts: {}"},

    "success_title":     {"ja": "成功",                           "en": "Success"},
    "run_mel_ok":        {"ja": "MEL スクリプト '{}' 実行完了",   "en": "MEL script '{}' executed."},
    "run_py_ok":         {"ja": "Python スクリプト '{}' 実行完了", "en": "Python script '{}' executed."},
    "run_err_title":     {"ja": "実行エラー",                     "en": "Execution Error"},
    "run_err_msg":       {"ja": "スクリプトの実行エラー: {}",     "en": "Failed to run script: {}"},

    "credit":            {"ja": "Developed by seitanmen",        "en": "Developed by seitanmen"},
}


class MayaScriptsManagerUI:
    def __init__(self):
        self.windowName = "MayaScriptsManagerWindow"
        self.Scripts = {}
        self.selectedScriptName = None  # 現在選択中のスクリプト名 / currently selected
        self.scriptButtons = {}         # スクリプト名 -> iconTextButton
        # このスクリプト自身の場所（アイコン/.env の相対解決に使用）
        try:
            self.baseDir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # exec() 経由で __file__ が無い場合
            self.baseDir = ""
        # .env から設定を取得（リポジトリパス・言語）
        env = self.loadEnv()
        self.repoPath = env.get("SCRIPT_REPO_PATH", "")
        self.lang = self._pickLang(env.get("LANG", ""))
        self.configFile = os.path.join(
            cmds.internalVar(userAppDir=True),
            "maya_scripts_manager_config.json"
        )
        self.loadScripts()  # 起動時にスクリプトを読み込み

    # ---- i18n helpers ----------------------------------------------------
    def _pickLang(self, pref):
        """使用言語を決定する。.env の LANG を優先し、無ければ Maya UI 言語。"""
        p = (pref or "").strip().lower()
        if p.startswith("ja"):
            return "ja"
        if p.startswith("en"):
            return "en"
        try:
            ui = (cmds.about(uiLanguage=True) or "").lower()
        except Exception:
            ui = ""
        return "ja" if ui.startswith("ja") else "en"

    def tr(self, key, *args):
        """翻訳文字列を返す（フォーマット引数対応）。未定義は key を返す。"""
        entry = STRINGS.get(key, {})
        s = entry.get(self.lang) or entry.get("en") or key
        if args:
            try:
                s = s.format(*args)
            except Exception:
                pass
        return s

    def loadEnv(self):
        """スクリプトと同じ場所の .env を読み込み、KEY=VALUE の辞書を返す。

        外部ライブラリに依存しない簡易パーサ。# はコメント、値の前後の
        引用符は除去する。.env が無い場合は空の辞書を返す。
        """
        env = {}
        if not self.baseDir:
            return env
        envPath = os.path.join(self.baseDir, ".env")
        if not os.path.isfile(envPath):
            return env
        try:
            with open(envPath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip().strip('"').strip("'")
        except Exception as e:
            print("MayaScriptsManager: .env load failed: {}".format(str(e)))
        return env

    def repoStartDir(self):
        """ファイルダイアログの初期ディレクトリ（.env のパスが実在すれば返す）"""
        if self.repoPath and os.path.isdir(self.repoPath):
            return self.repoPath
        return ""

    def makeButtonRow(self, parent, buttons, height=28):
        """幅いっぱいに均等分割して伸縮するボタン行を作成する。

        buttons: [(label, command), ...]
        formLayout + attachPosition で各ボタンをウィンドウ幅に追従させる。
        """
        row = cmds.formLayout(parent=parent, height=height)
        n = len(buttons)
        created = [cmds.button(label=lbl, command=cmd, parent=row)
                   for lbl, cmd in buttons]
        af = []
        ap = []
        for i, b in enumerate(created):
            af.append((b, 'top', 0))
            af.append((b, 'bottom', 0))
            if i == 0:
                af.append((b, 'left', 0))
            else:
                ap.append((b, 'left', 2, int(round(100.0 * i / n))))
            if i == n - 1:
                af.append((b, 'right', 0))
            else:
                ap.append((b, 'right', 2, int(round(100.0 * (i + 1) / n))))
        cmds.formLayout(row, edit=True, attachForm=af, attachPosition=ap)
        return row

    def create(self):
        if cmds.window(self.windowName, exists=True):
            cmds.deleteUI(self.windowName)

        # sizeable=True でリサイズ可能。初期サイズのみ指定し、以降は伸縮追従
        cmds.window(self.windowName, title="Maya Scripts Manager",
                    widthHeight=(500, 640), sizeable=True)

        # メインは formLayout。タブを上下左右に固定し、クレジットを下端に固定
        mainForm = cmds.formLayout(numberOfDivisions=100)

        tabs = cmds.tabLayout(parent=mainForm,
                              innerMarginWidth=5,
                              innerMarginHeight=5)

        # ===== タブ1: 登録 / 編集（formLayout で縦横伸縮） =====
        registerTab = cmds.formLayout(parent=tabs, numberOfDivisions=100)

        nameLabel = cmds.text(label=self.tr("name_label"), parent=registerTab)
        self.scriptNameField = cmds.textField(parent=registerTab)
        tipLabel = cmds.text(label=self.tr("desc_label"), parent=registerTab)
        self.tooltipsField = cmds.textField(parent=registerTab)
        typeLabel = cmds.text(label=self.tr("type_label"), parent=registerTab)
        self.scriptTypeRadio = cmds.radioButtonGrp(
            parent=registerTab,
            numberOfRadioButtons=2,
            labelArray2=['MEL', 'Python'],
            select=1  # デフォルトは MEL
        )
        # 編集対象を小さなタブで切り替え（スクリプト / ダブルクリック）
        # ※ダブルクリックは command と sourceType を共有（上のタイプで実行）
        self.editTabs = cmds.tabLayout(parent=registerTab,
                                       innerMarginWidth=3, innerMarginHeight=3)

        scriptTabForm = cmds.formLayout(parent=self.editTabs)
        self.scriptArea = cmds.scrollField(parent=scriptTabForm, wordWrap=True)
        cmds.formLayout(scriptTabForm, edit=True, attachForm=[
            (self.scriptArea, 'top', 0), (self.scriptArea, 'bottom', 0),
            (self.scriptArea, 'left', 0), (self.scriptArea, 'right', 0)])

        dcTabForm = cmds.formLayout(parent=self.editTabs)
        self.doubleClickArea = cmds.scrollField(parent=dcTabForm, wordWrap=True)
        cmds.formLayout(dcTabForm, edit=True, attachForm=[
            (self.doubleClickArea, 'top', 0), (self.doubleClickArea, 'bottom', 0),
            (self.doubleClickArea, 'left', 0), (self.doubleClickArea, 'right', 0)])

        cmds.tabLayout(self.editTabs, edit=True, tabLabel=[
            (scriptTabForm, self.tr("tab_script")),
            (dcTabForm, self.tr("tab_dc"))
        ])

        # アイコン選択行（フィールドが伸縮、ボタンは固定幅）
        iconRow = cmds.rowLayout(numberOfColumns=2, adjustableColumn=1,
                                 columnAttach=[(1, 'both', 0), (2, 'both', 4)],
                                 parent=registerTab)
        self.iconPathField = cmds.textField(parent=iconRow)
        cmds.button(label=self.tr("browse_icon"), command=self.selectIcon, parent=iconRow)
        cmds.setParent('..')

        registerBtn = cmds.button(label=self.tr("register_btn"),
                                  command=self.registerScript, parent=registerTab)

        # レイアウト定義：上部フィールド群は固定高で上から連結、
        # 入力欄タブが中央で縦に伸び、下部（icon/登録）はボタン下端に固定
        cmds.formLayout(
            registerTab, edit=True,
            attachForm=[
                (nameLabel, 'top', 6), (nameLabel, 'left', 6),
                (self.scriptNameField, 'left', 6), (self.scriptNameField, 'right', 6),
                (tipLabel, 'left', 6),
                (self.tooltipsField, 'left', 6), (self.tooltipsField, 'right', 6),
                (typeLabel, 'left', 6),
                (self.scriptTypeRadio, 'left', 6),
                (self.editTabs, 'left', 6), (self.editTabs, 'right', 6),
                (iconRow, 'left', 6), (iconRow, 'right', 6),
                (registerBtn, 'left', 6), (registerBtn, 'right', 6),
                (registerBtn, 'bottom', 6),
            ],
            attachControl=[
                (self.scriptNameField, 'top', 2, nameLabel),
                (tipLabel, 'top', 6, self.scriptNameField),
                (self.tooltipsField, 'top', 2, tipLabel),
                (typeLabel, 'top', 6, self.tooltipsField),
                (self.scriptTypeRadio, 'top', 2, typeLabel),
                # 入力欄タブが中央で縦横に伸びる（タイプの下〜アイコン行の上）
                (self.editTabs, 'top', 6, self.scriptTypeRadio),
                (self.editTabs, 'bottom', 6, iconRow),
                (iconRow, 'bottom', 6, registerBtn),
            ]
        )

        # ===== タブ2: スクリプトリスト（formLayout で縦横伸縮） =====
        listTab = cmds.formLayout(parent=tabs, numberOfDivisions=100)

        listLabel = cmds.text(label=self.tr("list_label"), parent=listTab)
        self.scriptScroll = cmds.scrollLayout(parent=listTab, childResizable=True)
        # 行を並べるためのコンテナ（scrollLayout の子は1つの前提）
        self.scriptListCol = cmds.columnLayout(
            parent=self.scriptScroll,
            adjustableColumn=True,
            rowSpacing=2
        )

        ioRow = self.makeButtonRow(listTab, [
            (self.tr("export_btn"), self.exportScripts),
            (self.tr("import_btn"), self.importScripts),
        ])
        actionRow = self.makeButtonRow(listTab, [
            (self.tr("run_btn"), self.executeSelectedScript),
            (self.tr("delete_btn"), self.deleteSelectedScript),
        ])

        cmds.formLayout(
            listTab, edit=True,
            attachForm=[
                (listLabel, 'top', 6), (listLabel, 'left', 6),
                (self.scriptScroll, 'left', 6), (self.scriptScroll, 'right', 6),
                (ioRow, 'left', 6), (ioRow, 'right', 6),
                (actionRow, 'left', 6), (actionRow, 'right', 6),
                (actionRow, 'bottom', 6),
            ],
            attachControl=[
                (self.scriptScroll, 'top', 2, listLabel),
                (self.scriptScroll, 'bottom', 6, ioRow),
                (ioRow, 'bottom', 6, actionRow),
            ]
        )

        # タブのラベルを設定
        cmds.tabLayout(tabs, edit=True, tabLabel=[
            (registerTab, self.tr("tab_register")),
            (listTab, self.tr("tab_list"))
        ])

        # クレジット（タブ外・下端に固定）
        creditText = cmds.text(label=self.tr("credit"),
                               font="smallPlainLabelFont",
                               align="right", parent=mainForm)

        # メイン formLayout：タブが上部で伸縮、クレジットが下端に固定
        cmds.formLayout(
            mainForm, edit=True,
            attachForm=[
                (tabs, 'top', 4), (tabs, 'left', 4), (tabs, 'right', 4),
                (creditText, 'left', 6), (creditText, 'right', 6),
                (creditText, 'bottom', 4),
            ],
            attachControl=[
                (tabs, 'bottom', 4, creditText),
            ]
        )

        cmds.showWindow(self.windowName)
        self.refreshScriptList()

    def selectIcon(self, *args):
        """アイコンファイル選択ダイアログ"""
        iconPath = cmds.fileDialog2(
            fileMode=1,  # ファイル選択
            fileFilter="Image Files (*.png *.jpg *.xpm)",
            dialogStyle=2
        )

        if iconPath:
            cmds.textField(self.iconPathField, edit=True, text=iconPath[0])

    def registerScript(self, *args):
        """スクリプトの登録"""
        scriptName = cmds.textField(self.scriptNameField, q=True, text=True)
        scriptContent = cmds.scrollField(self.scriptArea, q=True, text=True)
        doubleClickContent = cmds.scrollField(self.doubleClickArea, q=True, text=True)
        scriptTooltips = cmds.textField(self.tooltipsField, q=True, text=True)
        iconPath = cmds.textField(self.iconPathField, q=True, text=True)
        scriptType = self.getSelectedType()

        if not scriptName or not scriptContent:
            cmds.confirmDialog(title=self.tr("err_title"),
                               message=self.tr("err_name_content"))
            return

        # スクリプト情報を辞書に保存
        self.Scripts[scriptName] = {
            "content": scriptContent,
            "doubleClickContent": doubleClickContent,  # ダブルクリック時に実行（任意）
            "tooltips": scriptTooltips,
            "icon": iconPath,
            "type": scriptType  # "mel" または "python"
        }

        self.saveScripts()
        self.refreshScriptList()

        # フィールドをクリア
        cmds.textField(self.scriptNameField, edit=True, text="")
        cmds.scrollField(self.scriptArea, edit=True, text="")
        cmds.scrollField(self.doubleClickArea, edit=True, text="")
        cmds.textField(self.tooltipsField, edit=True, text="")
        cmds.textField(self.iconPathField, edit=True, text="")
        cmds.radioButtonGrp(self.scriptTypeRadio, edit=True, select=1)
        # 表示をスクリプトタブに戻す
        cmds.tabLayout(self.editTabs, edit=True, selectTabIndex=1)

    def getSelectedType(self):
        """ラジオボタンの選択から "mel" / "python" を返す"""
        sel = cmds.radioButtonGrp(self.scriptTypeRadio, query=True, select=True)
        return "python" if sel == 2 else "mel"

    def resolveScriptType(self, script_info):
        """スクリプトのタイプを取得する。

        保存済みの "type" があればそれを使用（自動選択）。
        旧JSON等でタイプ未設定の場合は従来どおりダイアログで確認する（後方互換）。
        戻り値: "mel" / "python" / None（キャンセル）
        """
        scriptType = script_info.get("type", "")
        if scriptType in ("mel", "python"):
            return scriptType

        # 後方互換: タイプ未設定のスクリプトはダイアログで確認
        cancel = self.tr("btn_cancel")
        result = cmds.confirmDialog(
            title=self.tr("scripttype_title"),
            message=self.tr("scripttype_msg"),
            button=['MEL', 'Python', cancel],
            defaultButton='MEL',
            cancelButton=cancel,
            dismissString=cancel
        )
        if result == 'MEL':
            return "mel"
        elif result == 'Python':
            return "python"
        return None

    def selectScript(self, scriptName, *args):
        """スクリプト選択時の処理（行クリックで呼ばれる）"""
        self.selectedScriptName = scriptName
        self.highlightSelected(scriptName)

        script_info = self.Scripts.get(scriptName, {})

        cmds.textField(self.scriptNameField, edit=True, text=scriptName)
        cmds.scrollField(self.scriptArea, edit=True, text=script_info.get("content", ""))
        cmds.scrollField(self.doubleClickArea, edit=True, text=script_info.get("doubleClickContent", ""))
        cmds.textField(self.tooltipsField, edit=True, text=script_info.get("tooltips", ""))
        cmds.textField(self.iconPathField, edit=True, text=script_info.get("icon", ""))

        # 保存済みタイプをラジオボタンに反映（未設定なら MEL）
        storedType = script_info.get("type", "")
        cmds.radioButtonGrp(self.scriptTypeRadio, edit=True,
                            select=(2 if storedType == "python" else 1))

        # 表示をスクリプトタブに戻す
        cmds.tabLayout(self.editTabs, edit=True, selectTabIndex=1)

    def addToShelf(self, scriptName=None, *args):
        """現在のシェルフタブにスクリプトを追加（行のダブルクリックで呼ばれる）"""
        if scriptName is None:
            scriptName = self.selectedScriptName
        if not scriptName:
            cmds.confirmDialog(title=self.tr("err_title"),
                               message=self.tr("err_select_script"))
            return

        selectedScript = scriptName
        script_info = self.Scripts.get(selectedScript, {})

        # シェルフにボタンを追加
        gShelfTopLevel = mel.eval('$gShelfTopLevel=$gShelfTopLevel')
        currentShelfTab = cmds.tabLayout(gShelfTopLevel, query=True, selectTab=True)

        # アイコンパスの確認
        icon = script_info.get("icon", "commandButton.png")

        # スクリプトタイプを解決（保存済みなら自動、未設定ならダイアログ）
        sourceType = self.resolveScriptType(script_info)
        if sourceType is None:
            return  # キャンセルされた場合は何もしない

        command = script_info["content"]

        # シェルフボタン作成
        shelfButtonArgs = {
            "parent": currentShelfTab,
            "label": selectedScript,
            "command": command,
            "sourceType": sourceType,  # MELかPythonか（登録時のタイプを自動使用）
            "image": icon,
            "annotation": script_info.get("tooltips", selectedScript)  # Tooltips、なければ名前
        }

        # ダブルクリックスクリプトが登録されていれば設定
        # ※doubleClickCommand は command と sourceType を共有する（Maya仕様）
        doubleClickContent = script_info.get("doubleClickContent", "")
        if doubleClickContent:
            shelfButtonArgs["doubleClickCommand"] = doubleClickContent

        cmds.shelfButton(**shelfButtonArgs)

    def saveScripts(self):
        """スクリプトをJSONファイルに保存"""
        try:
            export_data = {}
            for name, script_info in self.Scripts.items():
                export_data[name] = {
                    "content": script_info.get("content", ""),
                    "doubleClickContent": script_info.get("doubleClickContent", ""),
                    "tooltips": script_info.get("tooltips", ""),
                    "icon": script_info.get("icon", ""),
                    "type": script_info.get("type", "")
                }

            with open(self.configFile, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            print("MayaScriptsManager: scripts saved.")
        except Exception as e:
            cmds.confirmDialog(title=self.tr("save_err_title"),
                               message=self.tr("save_err_msg", str(e)))

    def loadScripts(self):
        """JSONファイルからスクリプトを読み込み"""
        try:
            if os.path.exists(self.configFile):
                with open(self.configFile, 'r', encoding='utf-8') as f:
                    loaded_scripts = json.load(f)

                # 辞書の構造を確認しながら読み込み（旧JSONは新キーが無いので空で補完）
                self.Scripts = {}
                for name, script_info in loaded_scripts.items():
                    self.Scripts[name] = {
                        "content": script_info.get("content", ""),
                        "doubleClickContent": script_info.get("doubleClickContent", ""),
                        "tooltips": script_info.get("tooltips", ""),
                        "icon": script_info.get("icon", ""),
                        "type": script_info.get("type", "")
                    }
                print("MayaScriptsManager: scripts loaded.")
        except Exception as e:
            cmds.confirmDialog(title=self.tr("load_err_title"),
                               message=self.tr("load_err_msg", str(e)))

    def refreshScriptList(self):
        """スクリプトリストを更新（アイコン＋名前の行を再生成）"""
        # 既存の行を削除
        existing = cmds.columnLayout(self.scriptListCol, query=True, childArray=True) or []
        for child in existing:
            cmds.deleteUI(child)
        self.scriptButtons = {}

        # 各スクリプトを「アイコン＋名前」の行として追加（項目ごとに枠で囲む）
        for scriptName in self.Scripts.keys():
            info = self.Scripts[scriptName]
            icon = self.resolveIcon(info.get("icon", ""))
            # 項目ごとの枠（境界を明示）
            # ※ -borderStyle は新しいMayaで廃止フラグのため使用しない
            frame = cmds.frameLayout(
                parent=self.scriptListCol,
                labelVisible=False,
                borderVisible=True,
                collapsable=False,
                marginWidth=2,
                marginHeight=2
            )
            btn = cmds.iconTextButton(
                parent=frame,
                style='iconAndTextHorizontal',
                image1=icon,
                label=scriptName,
                height=34,
                annotation=info.get("tooltips", "") or scriptName,
                command=partial(self.selectScript, scriptName),
                doubleClickCommand=partial(self.addToShelf, scriptName)
            )
            self.scriptButtons[scriptName] = btn
            cmds.setParent(self.scriptListCol)

        # 選択状態を再適用（削除された場合は解除）
        if self.selectedScriptName in self.scriptButtons:
            self.highlightSelected(self.selectedScriptName)
        else:
            self.selectedScriptName = None

    def resolveIcon(self, iconPath):
        """アイコンのパスを解決する。

        1) 絶対パスが実在すればそれを使用（本番の 共有ドライブ等）
        2) 無ければファイル名をスクリプト位置からの相対で探索
           （repo/icons/ , icons/ , 同階層）
        3) それでも無ければ Maya 既定アイコン
        """
        if iconPath and os.path.isfile(iconPath):
            return iconPath
        baseName = os.path.basename(iconPath) if iconPath else ""
        if baseName and self.baseDir:
            candidates = [
                os.path.join(self.baseDir, "repo", "icons", baseName),
                os.path.join(self.baseDir, "icons", baseName),
                os.path.join(self.baseDir, baseName),
            ]
            for cand in candidates:
                if os.path.isfile(cand):
                    return cand
        return "commandButton.png"

    def highlightSelected(self, scriptName):
        """選択中の行だけ背景色を付けて強調する"""
        for name, btn in self.scriptButtons.items():
            if name == scriptName:
                cmds.iconTextButton(btn, edit=True,
                                    enableBackground=True,
                                    backgroundColor=(0.32, 0.36, 0.5))
            else:
                cmds.iconTextButton(btn, edit=True, enableBackground=False)

    def exportScripts(self, *args):
        """スクリプトを外部ファイルにエクスポート"""
        dialogArgs = dict(
            fileMode=0,  # 保存ファイル選択
            fileFilter="JSON Files (*.json)",
            dialogStyle=2
        )
        startDir = self.repoStartDir()  # .env のリポジトリパス
        if startDir:
            dialogArgs["startingDirectory"] = startDir
        exportPath = cmds.fileDialog2(**dialogArgs)

        if exportPath:
            try:
                with open(exportPath[0], 'w', encoding='utf-8') as f:
                    json.dump(self.Scripts, f, indent=4, ensure_ascii=False)
                cmds.confirmDialog(title=self.tr("export_ok_title"),
                                   message=self.tr("export_ok_msg", exportPath[0]))
            except Exception as e:
                cmds.confirmDialog(title=self.tr("export_err_title"),
                                   message=self.tr("export_err_msg", str(e)))

    def importScripts(self, *args):
        """外部ファイルからスクリプトをインポート"""
        dialogArgs = dict(
            fileMode=1,  # ファイル選択
            fileFilter="JSON Files (*.json)",
            dialogStyle=2
        )
        startDir = self.repoStartDir()  # .env のリポジトリパス
        if startDir:
            dialogArgs["startingDirectory"] = startDir
        importPath = cmds.fileDialog2(**dialogArgs)

        if importPath:
            try:
                with open(importPath[0], 'r', encoding='utf-8') as f:
                    imported_scripts = json.load(f)

                # 既存のスクリプトに追加（上書きを避けるため）
                for name, content in imported_scripts.items():
                    if name not in self.Scripts:
                        # 旧JSON互換: 新キーが無ければ空文字で補完
                        self.Scripts[name] = {
                            "content": content.get("content", ""),
                            "doubleClickContent": content.get("doubleClickContent", ""),
                            "tooltips": content.get("tooltips", ""),
                            "icon": content.get("icon", ""),
                            "type": content.get("type", "")
                        }

                self.saveScripts()
                self.refreshScriptList()

                cmds.confirmDialog(title=self.tr("import_ok_title"),
                                   message=self.tr("import_ok_msg", importPath[0]))
            except Exception as e:
                cmds.confirmDialog(title=self.tr("import_err_title"),
                                   message=self.tr("import_err_msg", str(e)))

    def executeSelectedScript(self, *args):
        """選択したスクリプトを実行"""
        selectedScript = self.selectedScriptName

        if not selectedScript:
            cmds.confirmDialog(title=self.tr("err_title"),
                               message=self.tr("err_select_script"))
            return

        script_info = self.Scripts.get(selectedScript, {})
        scriptContent = script_info.get("content", "")

        # スクリプトタイプを解決（保存済みなら自動、未設定ならダイアログ）
        scriptType = self.resolveScriptType(script_info)
        if scriptType is None:
            return  # キャンセルされた場合は何もしない

        try:
            if scriptType == 'mel':
                mel.eval(scriptContent)
                cmds.confirmDialog(title=self.tr("success_title"),
                                   message=self.tr("run_mel_ok", selectedScript))
            elif scriptType == 'python':
                exec(scriptContent)
                cmds.confirmDialog(title=self.tr("success_title"),
                                   message=self.tr("run_py_ok", selectedScript))
        except Exception as e:
            cmds.confirmDialog(title=self.tr("run_err_title"),
                               message=self.tr("run_err_msg", str(e)))

    def deleteSelectedScript(self, *args):
        """選択したスクリプトを削除"""
        selectedScript = self.selectedScriptName

        if not selectedScript:
            cmds.confirmDialog(title=self.tr("err_title"),
                               message=self.tr("err_select_delete"))
            return

        # スクリプトを辞書から削除
        del self.Scripts[selectedScript]
        self.selectedScriptName = None

        self.saveScripts()
        self.refreshScriptList()

        # フィールドをクリア
        cmds.textField(self.scriptNameField, edit=True, text="")
        cmds.scrollField(self.scriptArea, edit=True, text="")


# UIを作成 / Create and show the UI
def showScriptManager():
    script_manager = MayaScriptsManagerUI()
    script_manager.create()


showScriptManager()
