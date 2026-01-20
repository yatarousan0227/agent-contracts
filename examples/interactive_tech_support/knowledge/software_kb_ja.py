"""ソフトウェアトラブルシューティングナレッジベース（日本語版）"""

from typing import Any

SOFTWARE_KB_JA: dict[str, dict[str, Any]] = {
    "crash": {
        "keywords": [
            "クラッシュ",
            "フリーズ",
            "応答なし",
            "動作停止",
            "固まる",
            "crash",
            "freeze",
            "hung",
        ],
        "issues": {
            "app_crash": {
                "title": "アプリケーションのクラッシュ",
                "steps": [
                    "1. 他のアプリケーションで作業中のファイルを保存",
                    "2. クラッシュしたアプリケーションを強制終了（タスクマネージャー > タスクの終了）",
                    "3. アプリケーションを再起動",
                    "4. アプリケーションの更新を確認",
                    "5. アプリケーションのキャッシュ/一時ファイルをクリア",
                    "6. 問題が続く場合はアプリケーションを再インストール",
                ],
                "follow_up": "アプリケーションは正常に動作するようになりましたか？",
            },
            "system_freeze": {
                "title": "システムのフリーズ",
                "steps": [
                    "1. 数分待つ - システムが回復する可能性があります",
                    "2. Ctrl+Alt+Deleteを押してみる",
                    "3. 可能であれば作業を保存して再起動",
                    "4. 再起動後にドライバーの更新を確認",
                    "5. Windowsメモリ診断を実行",
                    "6. イベントビューアーでエラーログを確認",
                ],
                "follow_up": "フリーズの問題は解決しましたか？",
            },
        },
    },
    "slow_computer": {
        "keywords": [
            "遅い",
            "重い",
            "パフォーマンス",
            "時間がかかる",
            "もっさり",
            "slow",
            "laggy",
            "sluggish",
        ],
        "issues": {
            "general_slowness": {
                "title": "コンピューターの動作が遅い",
                "steps": [
                    "1. タスクマネージャーを開いてCPU/メモリ使用率を確認",
                    "2. 不要なバックグラウンドアプリケーションを終了",
                    "3. ディスクの空き容量を確認（10%以上を維持）",
                    "4. ディスククリーンアップユーティリティを実行",
                    "5. アンチウイルスでマルウェアスキャン",
                    "6. 不要なスタートアッププログラムを無効化",
                    "7. 常に遅い場合はRAMの増設を検討",
                ],
                "follow_up": "コンピューターの速度は改善しましたか？",
            },
            "slow_startup": {
                "title": "起動が遅い",
                "steps": [
                    "1. タスクマネージャー > スタートアップタブを開く",
                    "2. 不要なスタートアッププログラムを無効化",
                    "3. ディスククリーンアップを実行",
                    "4. Windowsアップデートを確認",
                    "5. HDDを使用している場合はSSDへのアップグレードを検討",
                ],
                "follow_up": "起動時間は改善しましたか？",
            },
        },
    },
    "install": {
        "keywords": [
            "インストール",
            "セットアップ",
            "インストールできない",
            "install",
            "setup",
        ],
        "issues": {
            "install_failed": {
                "title": "インストールが失敗した",
                "steps": [
                    "1. 管理者として実行でインストーラーを起動",
                    "2. アンチウイルスを一時的に無効化",
                    "3. ディスクの空き容量を確認",
                    "4. インストーラーを再度ダウンロード",
                    "5. 以前のバージョンをアンインストールする必要があるか確認",
                    "6. システム要件を満たしているか確認",
                ],
                "follow_up": "ソフトウェアをインストールできましたか？",
            },
        },
    },
    "update": {
        "keywords": [
            "アップデート",
            "更新",
            "更新できない",
            "update",
            "updating",
        ],
        "issues": {
            "update_failed": {
                "title": "アップデートが失敗した",
                "steps": [
                    "1. コンピューターを再起動して再試行",
                    "2. インターネット接続を確認",
                    "3. ディスクの空き容量が十分か確認",
                    "4. Windows Update トラブルシューターを実行",
                    "5. Windows Updateのキャッシュをクリア",
                    "6. 手動でアップデートをダウンロードして試す",
                ],
                "follow_up": "アップデートは正常に完了しましたか？",
            },
        },
    },
    "error": {
        "keywords": [
            "エラー",
            "エラーメッセージ",
            "エラーコード",
            "例外",
            "error",
            "exception",
        ],
        "issues": {
            "generic_error": {
                "title": "アプリケーションエラー",
                "steps": [
                    "1. 正確なエラーメッセージまたはコードを記録",
                    "2. 特定のエラーをオンラインで検索",
                    "3. アプリケーションを再起動",
                    "4. アプリケーションの更新を確認",
                    "5. アプリケーションを修復または再インストール",
                    "6. アプリケーションログで詳細を確認",
                ],
                "follow_up": "エラーは解決しましたか？",
            },
            "blue_screen": {
                "title": "ブルースクリーンエラー（BSOD）",
                "steps": [
                    "1. 表示されたエラーコードを記録",
                    "2. コンピューターを再起動",
                    "3. 最近のドライバーやソフトウェアの変更を確認",
                    "4. Windowsメモリ診断を実行",
                    "5. すべてのドライバーを更新",
                    "6. システムファイルチェッカーを実行（sfc /scannow）",
                ],
                "follow_up": "ブルースクリーンエラーは発生しなくなりましたか？",
            },
        },
    },
    "virus": {
        "keywords": [
            "ウイルス",
            "マルウェア",
            "感染",
            "アンチウイルス",
            "セキュリティ",
            "virus",
            "malware",
        ],
        "issues": {
            "malware_suspected": {
                "title": "マルウェア感染の疑い",
                "steps": [
                    "1. インターネットから切断",
                    "2. フルアンチウイルススキャンを実行",
                    "3. Malwarebytesまたは類似のマルウェア対策ツールを実行",
                    "4. 頑固なマルウェアにはセーフモードで起動",
                    "5. プログラムの追加と削除から不審なプログラムを削除",
                    "6. 影響を受けた場合はブラウザ設定をリセット",
                    "7. クリーニング後に重要なパスワードを変更",
                ],
                "follow_up": "マルウェアは除去されましたか？",
            },
        },
    },
    "browser": {
        "keywords": [
            "ブラウザ",
            "Chrome",
            "Firefox",
            "Edge",
            "Safari",
            "ウェブページ",
            "browser",
            "webpage",
        ],
        "issues": {
            "browser_slow": {
                "title": "ブラウザが遅い",
                "steps": [
                    "1. ブラウザのキャッシュとCookieをクリア",
                    "2. 不要な拡張機能を無効化",
                    "3. ブラウザを更新",
                    "4. 特定のサイトだけの問題か確認",
                    "5. ブラウザをデフォルト設定にリセット",
                    "6. 別のブラウザを試す",
                ],
                "follow_up": "ブラウザのパフォーマンスは改善しましたか？",
            },
            "page_not_loading": {
                "title": "ページが読み込まれない",
                "steps": [
                    "1. インターネット接続を確認",
                    "2. ページを更新してみる（Ctrl+F5）",
                    "3. ブラウザのキャッシュをクリア",
                    "4. シークレット/プライベートモードで試す",
                    "5. 拡張機能を一時的に無効化",
                    "6. isitdown.usでサイトがダウンしていないか確認",
                ],
                "follow_up": "ページは読み込まれるようになりましたか？",
            },
        },
    },
}


def search_software_kb_ja(query: str) -> dict[str, Any] | None:
    """ソフトウェアナレッジベースから関連する問題を検索します。

    Args:
        query: ユーザーのクエリ文字列。

    Returns:
        最も関連性の高い問題データ、または一致するものがない場合はNone。
    """
    query_lower = query.lower()

    # すべてのカテゴリを検索
    for category, data in SOFTWARE_KB_JA.items():
        keywords = data.get("keywords", [])

        # キーワードが一致するか確認
        for keyword in keywords:
            if keyword.lower() in query_lower:
                # 最初の関連する問題を返す
                issues = data.get("issues", {})
                if issues:
                    # クエリに基づいて特定の問題を見つけようとする
                    for issue_key, issue_data in issues.items():
                        issue_title = issue_data.get("title", "").lower()
                        if any(word in query_lower for word in issue_title.split()):
                            return {
                                "category": category,
                                "issue": issue_key,
                                **issue_data,
                            }

                    # デフォルトとして最初の問題を返す
                    first_issue = next(iter(issues.items()))
                    return {
                        "category": category,
                        "issue": first_issue[0],
                        **first_issue[1],
                    }

    return None
