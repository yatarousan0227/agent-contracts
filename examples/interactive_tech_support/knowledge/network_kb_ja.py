"""ネットワークトラブルシューティングナレッジベース（日本語版）"""

from typing import Any

NETWORK_KB_JA: dict[str, dict[str, Any]] = {
    "wifi": {
        "keywords": [
            "WiFi",
            "Wi-Fi",
            "ワイファイ",
            "無線",
            "無線LAN",
            "信号",
            "ホットスポット",
            "wifi",
            "wireless",
        ],
        "issues": {
            "no_connection": {
                "title": "WiFiに接続できない",
                "steps": [
                    "1. デバイスでWiFiが有効になっているか確認",
                    "2. 他のデバイスが同じネットワークに接続できるか確認",
                    "3. ルーター/モデムを再起動（30秒間電源を抜く）",
                    "4. ネットワークを削除して再接続",
                    "5. 無線ドライバーの更新を確認",
                    "6. ルーターに近づく",
                    "7. ネットワークが非表示の場合はSSIDを手動で入力",
                ],
                "follow_up": "WiFiに接続できるようになりましたか？",
            },
            "slow_wifi": {
                "title": "WiFi速度が遅い",
                "steps": [
                    "1. speedtest.netで速度テストを実行",
                    "2. 他のデバイスからの干渉を確認",
                    "3. ルーター設定でWiFiチャンネルを変更してみる",
                    "4. ルーターを中央の位置に移動",
                    "5. 利用可能であれば5GHz帯を使用",
                    "6. 帯域を消費するアプリケーションを確認",
                    "7. ルーターのファームウェアを更新",
                ],
                "follow_up": "WiFi速度は改善しましたか？",
            },
            "keeps_disconnecting": {
                "title": "WiFi接続が切断される",
                "steps": [
                    "1. WiFi信号強度を確認",
                    "2. 無線ネットワークドライバーを更新",
                    "3. WiFiアダプターの省電力設定を無効化",
                    "4. ネットワーク設定をリセット",
                    "5. ルーターの過熱を確認",
                    "6. 別のWiFiチャンネルを試す",
                ],
                "follow_up": "WiFi接続は安定しましたか？",
            },
        },
    },
    "internet": {
        "keywords": [
            "インターネット",
            "オンライン",
            "ウェブサイト",
            "接続",
            "ネット接続なし",
            "internet",
            "online",
            "connection",
        ],
        "issues": {
            "no_internet": {
                "title": "インターネットにアクセスできない",
                "steps": [
                    "1. WiFi/イーサネットが接続されているか確認",
                    "2. 異なるウェブサイトにアクセスしてみる",
                    "3. ルーターとモデムを再起動（30秒間電源を抜く）",
                    "4. ネットワークトラブルシューターを実行",
                    "5. DNSキャッシュをフラッシュ（ipconfig /flushdns）",
                    "6. Google DNS（8.8.8.8）を使用してみる",
                    "7. 問題が続く場合はISPに連絡",
                ],
                "follow_up": "インターネットにアクセスできるようになりましたか？",
            },
            "intermittent": {
                "title": "インターネット接続が不安定",
                "steps": [
                    "1. ケーブル接続を確認",
                    "2. 切断中の接続を監視",
                    "3. お住まいの地域でISPの障害がないか確認",
                    "4. ネットワークアダプタードライバーを更新",
                    "5. ルーターログでエラーを確認",
                    "6. 古いネットワーク機器の交換を検討",
                ],
                "follow_up": "インターネット接続は安定しましたか？",
            },
        },
    },
    "vpn": {
        "keywords": [
            "VPN",
            "仮想プライベートネットワーク",
            "トンネル",
            "リモートアクセス",
            "vpn",
            "tunnel",
        ],
        "issues": {
            "vpn_not_connecting": {
                "title": "VPNに接続できない",
                "steps": [
                    "1. まずインターネット接続を確認",
                    "2. VPN資格情報が正しいか確認",
                    "3. 別のVPNサーバーを試す",
                    "4. ファイアウォールがVPNをブロックしていないか確認",
                    "5. VPNクライアントソフトウェアを更新",
                    "6. 別のVPNプロトコルを試す（OpenVPN、IKEv2）",
                    "7. VPNサポートまたはIT部門に連絡",
                ],
                "follow_up": "VPNに接続できるようになりましたか？",
            },
            "vpn_slow": {
                "title": "VPN接続が遅い",
                "steps": [
                    "1. より近い場所のサーバーを試す",
                    "2. より高速なVPNプロトコルに切り替え",
                    "3. VPNなしでの基本インターネット速度を確認",
                    "4. 帯域を消費するアプリケーションを終了",
                    "5. WiFiの代わりにイーサネットで接続",
                ],
                "follow_up": "VPN速度は改善しましたか？",
            },
        },
    },
    "dns": {
        "keywords": [
            "DNS",
            "ドメイン",
            "名前解決",
            "サーバーが見つからない",
            "dns",
            "domain",
        ],
        "issues": {
            "dns_issues": {
                "title": "DNS解決の問題",
                "steps": [
                    "1. DNSキャッシュをフラッシュ: ipconfig /flushdns（Windows）",
                    "2. パブリックDNSを使用: 8.8.8.8 または 1.1.1.1",
                    "3. 特定のサイトだけの問題か確認",
                    "4. ルーターを再起動",
                    "5. hostsファイルに不正なエントリがないか確認",
                    "6. ネットワーク設定をリセット",
                ],
                "follow_up": "ウェブサイトは正常に読み込まれるようになりましたか？",
            },
        },
    },
    "router": {
        "keywords": [
            "ルーター",
            "モデム",
            "ゲートウェイ",
            "ネットワーク機器",
            "router",
            "modem",
        ],
        "issues": {
            "router_issues": {
                "title": "ルーターの問題",
                "steps": [
                    "1. ルーターの電源を入れ直す（30秒間電源を抜く）",
                    "2. すべてのケーブル接続を確認",
                    "3. 過熱を確認（換気を確保）",
                    "4. ルーターのファームウェアを更新",
                    "5. 必要に応じて工場出荷時設定にリセット",
                    "6. ルーターログでエラーを確認",
                ],
                "follow_up": "ルーターは正常に動作するようになりましたか？",
            },
            "cant_access_settings": {
                "title": "ルーター設定にアクセスできない",
                "steps": [
                    "1. ルーターのIPアドレスを確認（通常は192.168.1.1または192.168.0.1）",
                    "2. 別のブラウザを試す",
                    "3. ブラウザのキャッシュをクリア",
                    "4. WiFiの代わりにイーサネットで接続",
                    "5. ルーターがブリッジモードになっていないか確認",
                    "6. デフォルトのログイン資格情報を試す（ルーターのラベルを確認）",
                ],
                "follow_up": "ルーター設定にアクセスできるようになりましたか？",
            },
        },
    },
    "ethernet": {
        "keywords": [
            "イーサネット",
            "有線",
            "LAN",
            "ネットワークケーブル",
            "LANケーブル",
            "ethernet",
            "wired",
            "lan",
        ],
        "issues": {
            "no_ethernet": {
                "title": "イーサネットが動作しない",
                "steps": [
                    "1. ケーブルが両端でしっかり接続されているか確認",
                    "2. 別のイーサネットケーブルを試す",
                    "3. ルーターの別のポートを試す",
                    "4. ネットワークポートのリンクランプを確認",
                    "5. ネットワークアダプタードライバーを更新",
                    "6. ネットワークトラブルシューターを実行",
                ],
                "follow_up": "イーサネット接続は動作するようになりましたか？",
            },
        },
    },
}


def search_network_kb_ja(query: str) -> dict[str, Any] | None:
    """ネットワークナレッジベースから関連する問題を検索します。

    Args:
        query: ユーザーのクエリ文字列。

    Returns:
        最も関連性の高い問題データ、または一致するものがない場合はNone。
    """
    query_lower = query.lower()

    # すべてのカテゴリを検索
    for category, data in NETWORK_KB_JA.items():
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
