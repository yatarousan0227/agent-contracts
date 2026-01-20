"""一般的な技術質問のFAQデータ（日本語版）"""

from typing import Any

FAQ_DATA_JA: list[dict[str, Any]] = [
    {
        "keywords": [
            "パスワード",
            "パスワード忘れた",
            "パスワードリセット",
            "パスワード変更",
            "password",
        ],
        "question": "パスワードをリセットするには？",
        "answer": {
            "title": "パスワードリセットガイド",
            "content": (
                "パスワードをリセットするには：\n"
                "1. ログインページに移動\n"
                "2. 「パスワードを忘れた」または「パスワードをリセット」をクリック\n"
                "3. メールアドレスを入力\n"
                "4. メールでリセットリンクを確認\n"
                "5. リンクに従って新しいパスワードを作成\n"
                "\nヒント: 文字、数字、記号を含む強力なパスワードを使用してください。"
            ),
        },
    },
    {
        "keywords": [
            "バックアップ",
            "データバックアップ",
            "データ保存",
            "クラウドバックアップ",
            "backup",
        ],
        "question": "データをバックアップするには？",
        "answer": {
            "title": "データバックアップの選択肢",
            "content": (
                "データをバックアップする方法はいくつかあります：\n\n"
                "1. クラウドストレージ: Google Drive、Dropbox、OneDriveなどを使用\n"
                "2. 外付けドライブ: 外付けハードドライブやUSBにファイルをコピー\n"
                "3. 内蔵バックアップ: WindowsバックアップまたはTime Machine（Mac）を使用\n"
                "4. 自動バックアップ: スケジュールされたバックアップを設定\n"
                "\n推奨: 3-2-1ルールに従う - 3つのコピー、2つの異なるメディア、"
                "1つはオフサイト。"
            ),
        },
    },
    {
        "keywords": [
            "スクリーンショット",
            "画面キャプチャ",
            "プリントスクリーン",
            "画面撮影",
            "screenshot",
        ],
        "question": "スクリーンショットを撮るには？",
        "answer": {
            "title": "スクリーンショットの方法",
            "content": (
                "Windows:\n"
                "- PrtScn: 全画面\n"
                "- Alt+PrtScn: アクティブウィンドウ\n"
                "- Win+Shift+S: 切り取りツール\n\n"
                "Mac:\n"
                "- Cmd+Shift+3: 全画面\n"
                "- Cmd+Shift+4: 範囲選択\n"
                "- Cmd+Shift+5: スクリーンショットオプション"
            ),
        },
    },
    {
        "keywords": [
            "ズーム",
            "拡大",
            "縮小",
            "文字サイズ",
            "テキストサイズ",
            "zoom",
        ],
        "question": "ズームや文字サイズを変更するには？",
        "answer": {
            "title": "ズームと文字サイズ",
            "content": (
                "ブラウザ/アプリケーション:\n"
                "- Ctrl + プラス（+）: 拡大\n"
                "- Ctrl + マイナス（-）: 縮小\n"
                "- Ctrl + 0: ズームをリセット\n\n"
                "システム全体（Windows）:\n"
                "- 設定 > ディスプレイ > 拡大縮小とレイアウト\n\n"
                "システム全体（Mac）:\n"
                "- システム環境設定 > ディスプレイ > 解像度"
            ),
        },
    },
    {
        "keywords": [
            "コピー",
            "ペースト",
            "貼り付け",
            "カット",
            "切り取り",
            "クリップボード",
            "copy",
            "paste",
        ],
        "question": "コピー＆ペーストするには？",
        "answer": {
            "title": "コピー＆ペーストのショートカット",
            "content": (
                "Windows:\n"
                "- Ctrl+C: コピー\n"
                "- Ctrl+X: 切り取り\n"
                "- Ctrl+V: 貼り付け\n\n"
                "Mac:\n"
                "- Cmd+C: コピー\n"
                "- Cmd+X: 切り取り\n"
                "- Cmd+V: 貼り付け\n\n"
                "ヒント: Win+V（Windows）でクリップボード履歴を表示"
            ),
        },
    },
    {
        "keywords": [
            "ダークモード",
            "ナイトモード",
            "テーマ",
            "外観",
            "dark mode",
            "theme",
        ],
        "question": "ダークモードを有効にするには？",
        "answer": {
            "title": "ダークモードの有効化",
            "content": (
                "Windows 11/10:\n"
                "設定 > 個人用設定 > 色 > モードを選ぶ > ダーク\n\n"
                "Mac:\n"
                "システム環境設定 > 外観 > ダーク\n\n"
                "ブラウザ:\n"
                "ほとんどのブラウザはシステム設定に従いますが、ブラウザ設定で"
                "外観オプションを確認できます。"
            ),
        },
    },
    {
        "keywords": [
            "ストレージ",
            "ディスク容量",
            "空き容量",
            "ディスクがいっぱい",
            "storage",
            "disk space",
        ],
        "question": "ディスク容量を空けるには？",
        "answer": {
            "title": "ディスク容量の解放",
            "content": (
                "1. ごみ箱を空にする\n"
                "2. ディスククリーンアップ（Windows）またはストレージを最適化（Mac）を実行\n"
                "3. 使用していないプログラムをアンインストール\n"
                "4. ブラウザのキャッシュをクリア\n"
                "5. 大きなファイルを外部ストレージに移動\n"
                "6. 一時ファイルをクリア\n"
                "7. ストレージセンス（Windows）またはストレージを最適化（Mac）を使用"
            ),
        },
    },
    {
        "keywords": [
            "メール",
            "Outlook",
            "Gmail",
            "メール設定",
            "email",
            "mail",
        ],
        "question": "メールを設定するには？",
        "answer": {
            "title": "メール設定ガイド",
            "content": (
                "ほとんどのメールプロバイダーの場合：\n"
                "1. メールアプリ（Outlook、メールなど）を開く\n"
                "2. アカウントの追加をクリック\n"
                "3. メールアドレスを入力\n"
                "4. パスワードを入力\n"
                "5. 自動設定に従う\n\n"
                "手動設定の場合、以下が必要になることがあります：\n"
                "- IMAP/POPサーバーアドレス\n"
                "- 送信用SMTPサーバー\n"
                "- ポート番号とセキュリティ設定"
            ),
        },
    },
    {
        "keywords": [
            "再起動",
            "リブート",
            "シャットダウン",
            "電源を切る",
            "restart",
            "reboot",
            "shutdown",
        ],
        "question": "コンピューターを正しく再起動するには？",
        "answer": {
            "title": "正しい再起動/シャットダウン",
            "content": (
                "Windows:\n"
                "1. スタートメニューをクリック\n"
                "2. 電源ボタンをクリック\n"
                "3. 再起動またはシャットダウンを選択\n\n"
                "Mac:\n"
                "1. Appleメニューをクリック\n"
                "2. 再起動またはシステム終了を選択\n\n"
                "ヒント: 再起動前に必ずアプリケーションを閉じて作業を保存してください。"
            ),
        },
    },
    {
        "keywords": [
            "Bluetooth",
            "ブルートゥース",
            "ペアリング",
            "デバイス接続",
            "ワイヤレスデバイス",
            "bluetooth",
        ],
        "question": "Bluetoothデバイスを接続するには？",
        "answer": {
            "title": "Bluetoothペアリングガイド",
            "content": (
                "Windows:\n"
                "1. Bluetoothデバイスをペアリングモードにする\n"
                "2. 設定 > Bluetoothとデバイス > デバイスの追加\n"
                "3. リストからデバイスを選択\n\n"
                "Mac:\n"
                "1. Bluetoothデバイスをペアリングモードにする\n"
                "2. システム環境設定 > Bluetooth\n"
                "3. デバイスを選択して接続をクリック"
            ),
        },
    },
    {
        "keywords": [
            "タスクマネージャー",
            "プロセス",
            "実行中のプログラム",
            "強制終了",
            "task manager",
            "force quit",
        ],
        "question": "タスクマネージャーを開くまたはアプリを強制終了するには？",
        "answer": {
            "title": "タスクマネージャー / 強制終了",
            "content": (
                "Windows - タスクマネージャー:\n"
                "- Ctrl+Shift+Escを押す\n"
                "- またはタスクバーを右クリック > タスクマネージャー\n"
                "- アプリを選択してタスクの終了をクリック\n\n"
                "Mac - 強制終了:\n"
                "- Cmd+Option+Escを押す\n"
                "- またはAppleメニュー > 強制終了\n"
                "- アプリを選択して強制終了をクリック"
            ),
        },
    },
    {
        "keywords": [
            "二要素認証",
            "2FA",
            "認証",
            "検証",
            "two factor",
            "authentication",
        ],
        "question": "二要素認証（2FA）とは？",
        "answer": {
            "title": "二要素認証",
            "content": (
                "二要素認証は以下を要求することで追加のセキュリティを提供します：\n"
                "1. 知っているもの（パスワード）\n"
                "2. 持っているもの（電話、セキュリティキー）\n\n"
                "一般的な2FA方法:\n"
                "- SMSコード\n"
                "- 認証アプリ（Google Authenticator、Authy）\n"
                "- ハードウェアセキュリティキー\n\n"
                "推奨: すべての重要なアカウントで2FAを有効にしてください。"
            ),
        },
    },
]


def search_faq_ja(query: str) -> dict[str, Any] | None:
    """FAQデータから関連する回答を検索します。

    Args:
        query: ユーザーのクエリ文字列。

    Returns:
        最も関連性の高いFAQ回答、または一致するものがない場合はNone。
    """
    query_lower = query.lower()

    # すべてのFAQを検索
    for faq in FAQ_DATA_JA:
        keywords = faq.get("keywords", [])

        # キーワードが一致するか確認
        for keyword in keywords:
            if keyword.lower() in query_lower:
                return {
                    "question": faq.get("question", ""),
                    **faq.get("answer", {}),
                }

    return None


def get_all_faq_topics_ja() -> list[str]:
    """すべてのFAQトピックのリストを取得します。

    Returns:
        FAQ質問のリスト。
    """
    return [faq.get("question", "") for faq in FAQ_DATA_JA]
