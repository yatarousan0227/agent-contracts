"""
Test suite for sanitize_context.py

包括的なテスト:
- Helper関数のテスト
- 基本機能のテスト (dict/list/str/その他の型、再帰処理)
- Data URI のテスト
- JWT のテスト
- Base64/Base64URL のテスト
- Hex データのテスト
- Binary URL のテスト
- Edge cases のテスト (空文字列、oversized data、surrogate pairs)
- パラメータのテスト

方針:
- テストデータは可能な限り「妥当なエンコード」を生成して不安定要因を排除する
- data URI は中身のbase64妥当性を検証しない実装であっても、置換されることを確認する
  （将来、data URI の中身検証を仕様化する場合はテストを調整する）
"""

from __future__ import annotations

import base64
import binascii
import json
import pytest

from agent_contracts.utils.sanitize_context import (
    sanitize_for_llm_util,
    MAX_INPUT_LENGTH,
    _strip_ws,
    _add_b64_padding,
    _safe_b64decode_prefix,
    _classify_magic,
    _looks_like_base64,
    _is_likely_hex,
    _try_parse_jwt_alg,
    _safe_truncate,
)


class TestHelperFunctions:
    """Helper関数の単体テスト"""

    def test_strip_ws(self) -> None:
        assert _strip_ws("  hello  world  ") == "helloworld"
        assert _strip_ws("") == ""

    def test_add_b64_padding(self) -> None:
        assert _add_b64_padding("YQ") == "YQ=="
        assert _add_b64_padding("YWJj") == "YWJj"

    def test_classify_magic(self) -> None:
        assert _classify_magic(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20) == "image/png"
        assert _classify_magic(b"\xff\xd8\xff" + b"\x00" * 20) == "image/jpeg"
        assert _classify_magic(b"UNKNOWN") is None

    def test_safe_truncate(self) -> None:
        assert _safe_truncate("Hello", 3) == "Hel"
        assert _safe_truncate("Hello", 100) == "Hello"

    def test_safe_b64decode_prefix_standard(self) -> None:
        """標準base64のprefix decode"""
        # 妥当なPNG base64（固定の1x1 PNG）
        png_b64 = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
            "WjR9awAAAABJRU5ErkJggg=="
        )
        result = _safe_b64decode_prefix(png_b64, urlsafe=False, max_bytes=64)
        assert result is not None
        assert result.startswith(b"\x89PNG")

    def test_safe_b64decode_prefix_urlsafe(self) -> None:
        """base64urlのprefix decode（短すぎる入力に依存しない）"""
        data = base64.urlsafe_b64encode(b"hello world" * 10).decode().rstrip("=")
        result = _safe_b64decode_prefix(data, urlsafe=True, max_bytes=5)
        # max_bytes=5 だが、base64デコードは4バイト単位なので実際には6バイトまで取得される
        assert result is not None
        assert result.startswith(b"hello")
        assert len(result) >= 5  # 少なくとも5バイトは取得できている

    def test_safe_b64decode_prefix_invalid(self) -> None:
        """不正なbase64"""
        result = _safe_b64decode_prefix("!!!invalid!!!", urlsafe=False, max_bytes=64)
        assert result is None

    def test_looks_like_base64_standard(self) -> None:
        """標準base64の検出（妥当なbase64を生成して不安定要因を排除）"""
        long_b64 = base64.b64encode(b"A" * 200).decode()
        is_b64, urlsafe = _looks_like_base64(long_b64, min_length=128)
        assert is_b64 is True
        assert urlsafe is False

    def test_looks_like_base64_urlsafe(self) -> None:
        """base64urlの検出（urlsafe文字を必ず含める）"""
        raw = b"\xff" * 200  # urlsafe_b64encode すると '_' が出やすい
        long_urlsafe = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        assert ("-" in long_urlsafe) or ("_" in long_urlsafe)  # urlsafe文字が入っていることを前提化

        is_b64, urlsafe = _looks_like_base64(long_urlsafe, min_length=128)
        assert is_b64 is True
        assert urlsafe is True

    def test_looks_like_base64_too_short(self) -> None:
        """短すぎる文字列"""
        short = "ABC"
        is_b64, urlsafe = _looks_like_base64(short, min_length=128)
        assert is_b64 is False
        assert urlsafe is None

    def test_try_parse_jwt_alg_valid(self) -> None:
        """妥当なJWTのalg取得（テスト内で生成して固定値依存を排除）"""
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"123"}').decode().rstrip("=")
        sig = "abc"
        jwt = f"{header}.{payload}.{sig}"
        alg = _try_parse_jwt_alg(jwt)
        assert alg == "HS256"

    def test_try_parse_jwt_alg_invalid(self) -> None:
        """不正なJWT"""
        invalid_jwt = "not.a.jwt"
        alg = _try_parse_jwt_alg(invalid_jwt)
        assert alg is None

    def test_is_likely_hex_valid(self) -> None:
        """妥当なhexデータの検出"""
        hex_data = "deadbeef" * 20  # 160文字
        result = _is_likely_hex(hex_data, min_length=128)
        assert result is True

    def test_is_likely_hex_too_short(self) -> None:
        """短すぎるhexデータ"""
        short_hex = "deadbeef"
        result = _is_likely_hex(short_hex, min_length=128)
        assert result is False

    def test_safe_b64decode_prefix_oversized(self) -> None:
        oversized = "A" * (MAX_INPUT_LENGTH + 1)
        assert _safe_b64decode_prefix(oversized, urlsafe=False, max_bytes=64) is None

    def test_classify_magic_webp_and_mp4(self) -> None:
        webp_prefix = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 8
        mp4_prefix = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16
        assert _classify_magic(webp_prefix) == "image/webp"
        assert _classify_magic(mp4_prefix) == "video/mp4"

    def test_looks_like_base64_oversized(self) -> None:
        oversized = "A" * (MAX_INPUT_LENGTH + 1)
        is_b64, urlsafe = _looks_like_base64(oversized, min_length=128)
        assert is_b64 is False
        assert urlsafe is None

    def test_looks_like_base64_invalid_decode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        data = "A" * 128

        def _raise(*_args, **_kwargs):
            raise binascii.Error("bad")

        monkeypatch.setattr(base64, "b64decode", _raise)
        is_b64, urlsafe = _looks_like_base64(data, min_length=10)
        assert is_b64 is False
        assert urlsafe is None

    def test_looks_like_base64url_invalid_decode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        data = "-" * 130

        def _raise(*_args, **_kwargs):
            raise binascii.Error("bad")

        monkeypatch.setattr(base64, "b64decode", _raise)
        is_b64, urlsafe = _looks_like_base64(data, min_length=10)
        assert is_b64 is False
        assert urlsafe is None

    def test_is_likely_hex_edge_cases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        oversized = "a" * (MAX_INPUT_LENGTH + 1)
        assert _is_likely_hex(oversized, min_length=128) is False

        odd_length = "abc"
        assert _is_likely_hex(odd_length, min_length=1) is False

        data = "aa" * 64

        def _raise(*_args, **_kwargs):
            raise binascii.Error("bad")

        monkeypatch.setattr(binascii, "unhexlify", _raise)
        assert _is_likely_hex(data, min_length=128) is False

    def test_try_parse_jwt_alg_edge_cases(self) -> None:
        oversized = "a" * (MAX_INPUT_LENGTH + 1)
        assert _try_parse_jwt_alg(oversized) is None

        header = base64.urlsafe_b64encode(json.dumps({"typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"123"}').decode().rstrip("=")
        jwt = f"{header}.{payload}.sig"
        assert _try_parse_jwt_alg(jwt) is None

    def test_safe_truncate_high_surrogate(self) -> None:
        text = "A" + chr(0xD800) + "B"
        assert _safe_truncate(text, 2) == "A"


class TestBasicFunctionality:
    """基本機能のテスト"""

    def test_dict_list_types(self) -> None:
        assert sanitize_for_llm_util({"k": "v"}) == {"k": "v"}
        assert sanitize_for_llm_util([1, 2, 3]) == [1, 2, 3]
        assert sanitize_for_llm_util(123) == 123
        assert sanitize_for_llm_util(None) is None

    def test_recursive_processing(self) -> None:
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200).decode()
        data = {"nested": {"image": png}}
        result = sanitize_for_llm_util(data, base64_min_length=50)
        assert "[BASE64_DATA" in result["nested"]["image"]


class TestDataURI:
    """Data URI検出のテスト"""

    def test_data_uri_basic(self) -> None:
        # 妥当なbase64を用いたdata URI
        b64 = base64.b64encode(b"a" * 200).decode()
        uri = f"data:image/png;base64,{b64}"
        result = sanitize_for_llm_util(uri)
        assert result == "[DATA_URI:image/png]"

    def test_data_uri_with_magic(self) -> None:
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100).decode()
        uri = f"data:image/png;base64,{png}"
        result = sanitize_for_llm_util(uri, classify_base64_magic=True)
        assert result.startswith("[DATA_URI:")
        # magic分類を有効にしているため、image/pngが含まれることを期待
        assert "image/png" in result

    def test_short_data_uri_detection(self) -> None:
        """短いData URIが正しく検出されることを確認（max_str_length以下でも検知される）"""
        b64 = base64.b64encode(b"a").decode()  # YQ==
        short_uri = f"data:image/png;base64,{b64}"
        result = sanitize_for_llm_util(short_uri, max_str_length=1000)
        assert result == "[DATA_URI:image/png]"

    def test_data_uri_no_magic_classification(self) -> None:
        b64 = base64.b64encode(b"a" * 10).decode()
        uri = f"data:image/png;base64,{b64}"
        result = sanitize_for_llm_util(uri, classify_base64_magic=False)
        assert result == "[DATA_URI:image/png]"

    def test_data_uri_empty_payload(self) -> None:
        uri = "data:image/png;base64,"
        result = sanitize_for_llm_util(uri, classify_base64_magic=True)
        assert result == "[DATA_URI:image/png]"


class TestJWT:
    """JWT検出のテスト"""

    def test_jwt_detection(self) -> None:
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"1234567890"}').decode().rstrip("=")
        sig = "a" * 100
        jwt = f"{header}.{payload}.{sig}"
        result = sanitize_for_llm_util(jwt)
        assert result == "[JWT:HS256]"

    def test_short_jwt_detection(self) -> None:
        """短いJWTが正しく検出されることを確認"""
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"123"}').decode().rstrip("=")
        sig = "abc"
        short_jwt = f"{header}.{payload}.{sig}"
        result = sanitize_for_llm_util(short_jwt, max_str_length=1000)
        assert result == "[JWT:HS256]"


class TestBase64:
    """Base64データ検出のテスト"""

    def test_base64_detection(self) -> None:
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200).decode()
        result = sanitize_for_llm_util(png, base64_min_length=50, classify_base64_magic=True)
        assert result == "[BASE64_DATA:image/png]"

    def test_base64_min_length(self) -> None:
        short = base64.b64encode(b"A" * 30).decode()
        result = sanitize_for_llm_util(short, base64_min_length=200, max_str_length=1000)
        assert result == short

    def test_base64url(self) -> None:
        png = base64.urlsafe_b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200).decode().rstrip("=")
        result = sanitize_for_llm_util(png, base64_min_length=50)
        assert "[BASE64_DATA" in result

    def test_base64_without_magic(self) -> None:
        plain = base64.b64encode(b"hello world" * 20).decode()
        result = sanitize_for_llm_util(plain, base64_min_length=50, classify_base64_magic=True)
        assert result == "[BASE64_DATA]"


class TestHexData:
    """Hexデータ検出のテスト"""

    def test_hex_detection(self) -> None:
        # hexデータはbase64文字集合にも収まる可能性があるため、base64_min_lengthを大きくする
        hex_data = "deadbeef" * 30
        result = sanitize_for_llm_util(hex_data, hex_min_length=50, base64_min_length=500)
        assert result == "[HEX_DATA]"

    def test_hex_min_length(self) -> None:
        short_hex = "deadbeef"
        result = sanitize_for_llm_util(short_hex, hex_min_length=100, max_str_length=1000)
        assert result == short_hex


class TestBinaryURL:
    """Binary URL検出のテスト"""

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/image.png",
            "https://example.com/photo.jpg",
            "https://example.com/video.mp4",
        ],
    )
    def test_binary_url_detection(self, url: str) -> None:
        result = sanitize_for_llm_util(url, sanitize_binary_urls=True)
        assert result == "[BINARY_URL]"

    def test_binary_url_disabled(self) -> None:
        url = "https://example.com/image.png"
        result = sanitize_for_llm_util(url, sanitize_binary_urls=False)
        assert result == url


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_empty_string(self) -> None:
        assert sanitize_for_llm_util("") == ""

    def test_oversized_data(self) -> None:
        huge = "A" * (MAX_INPUT_LENGTH + 1)
        result = sanitize_for_llm_util(huge)
        assert result == "[OVERSIZED_DATA]"

    def test_truncation(self) -> None:
        # base64検出を避けるため、明らかに通常テキストの文字列を使用
        long_text = "This is a normal text. " * 100
        result = sanitize_for_llm_util(long_text, max_str_length=100, base64_min_length=10000)
        assert "[TRUNCATED:" in result
        assert len(result) < 150

    def test_surrogate_pair_truncation(self) -> None:
        text = "Hello😀World"
        truncated = _safe_truncate(text, 6)
        # high surrogate で終わっていないこと（不正サロゲートが混入した場合の防御）
        assert not (truncated and 0xD800 <= ord(truncated[-1]) <= 0xDBFF)

    def test_whitespace_handling(self) -> None:
        # 空白を含む文字列はbase64として検出されない（通常のテキストとして扱う）
        b64_with_ws = base64.b64encode(b"A" * 200).decode()
        spaced = f"  {b64_with_ws[:50]}\n{b64_with_ws[50:]}  "
        result = sanitize_for_llm_util(spaced, base64_min_length=50)
        # 空白が含まれているため、base64として検出されない
        # そのまま返されるか、長さによってはトランケートされる
        assert "[BASE64_DATA]" not in result
        # 空白を含む文字列がそのまま返されることを確認
        assert spaced == result or "[TRUNCATED:" in result


class TestParameters:
    """パラメータ動作のテスト"""

    def test_max_str_length_param(self) -> None:
        text = "This is a test string. " * 30  # 約690文字
        result1 = sanitize_for_llm_util(text, max_str_length=100, base64_min_length=10000)
        result2 = sanitize_for_llm_util(text, max_str_length=1000, base64_min_length=10000)
        assert "[TRUNCATED" in result1
        assert result2 == text

    def test_classify_base64_magic_param(self) -> None:
        png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200).decode()
        with_magic = sanitize_for_llm_util(png, base64_min_length=50, classify_base64_magic=True)
        without_magic = sanitize_for_llm_util(png, base64_min_length=50, classify_base64_magic=False)
        assert "image/png" in with_magic
        assert with_magic != without_magic

    def test_sanitize_binary_urls_param(self) -> None:
        url = "https://example.com/image.png"
        with_san = sanitize_for_llm_util(url, sanitize_binary_urls=True)
        without_san = sanitize_for_llm_util(url, sanitize_binary_urls=False)
        assert with_san == "[BINARY_URL]"
        assert without_san == url


class TestDesignIssues:
    """設計上の回帰（短い文字列でも検知される）を押さえるテスト"""

    def test_short_strings_skip_detection(self) -> None:
        # 短いData URI（max_str_length以下でも検知される）
        b64 = base64.b64encode(b"a").decode()
        short_data_uri = f"data:image/png;base64,{b64}"
        result = sanitize_for_llm_util(short_data_uri, max_str_length=1000)
        assert result == "[DATA_URI:image/png]"

        # 短いJWT（max_str_length以下でも検知される）
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"1"}').decode().rstrip("=")
        short_jwt = f"{header}.{payload}.sig"
        result = sanitize_for_llm_util(short_jwt, max_str_length=1000)
        assert result == "[JWT:HS256]"

        # 短いBinary URL（max_str_length以下でも検知される）
        short_url = "https://x.co/a.png"
        result = sanitize_for_llm_util(short_url, max_str_length=1000, sanitize_binary_urls=True)
        assert result == "[BINARY_URL]"
