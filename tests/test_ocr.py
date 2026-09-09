from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rx_strategist.ocr.gemini_ocr import GeminiPrescriptionOCR

SAMPLE_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "prescriptions"
    / "sample_prescription.png"
)
TRANSCRIPTION = (
    "55-year-old female with hypertension and type 2 diabetes.\n"
    "Losartan 50 mg OD PO.\n"
    "Metformin 500 mg BID PO.\n"
    "Kidney function is normal. No known allergies."
)


def test_missing_api_key_raises_value_error():
    with pytest.raises(ValueError, match="Gemini API key is required"):
        GeminiPrescriptionOCR(api_key="")


@patch("rx_strategist.ocr.gemini_ocr.genai.Client")
def test_ocr_image_returns_transcription(mock_client_cls):
    mock_response = MagicMock()
    mock_response.text = f"  {TRANSCRIPTION}  "
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    ocr = GeminiPrescriptionOCR(api_key="test-key")
    result = ocr.ocr_image(SAMPLE_IMAGE)

    assert result == TRANSCRIPTION
    mock_client.models.generate_content.assert_called_once()
    _, kwargs = mock_client.models.generate_content.call_args
    assert kwargs["model"] == "models/gemini-3.5-flash-lite"


@patch("rx_strategist.ocr.gemini_ocr.genai.Client")
def test_ocr_image_accepts_bytes(mock_client_cls):
    mock_response = MagicMock()
    mock_response.text = TRANSCRIPTION
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    ocr = GeminiPrescriptionOCR(api_key="test-key")
    result = ocr.ocr_image(SAMPLE_IMAGE.read_bytes(), mime_type="image/png")

    assert result == TRANSCRIPTION


@patch("rx_strategist.ocr.gemini_ocr.genai.Client")
def test_ocr_image_bytes_require_mime_type(mock_client_cls):
    mock_client_cls.return_value = MagicMock()
    ocr = GeminiPrescriptionOCR(api_key="test-key")

    with pytest.raises(ValueError, match="mime_type is required"):
        ocr.ocr_image(SAMPLE_IMAGE.read_bytes())


@patch("rx_strategist.ocr.gemini_ocr.genai.Client")
def test_missing_image_path_raises_file_not_found(mock_client_cls):
    mock_client_cls.return_value = MagicMock()
    ocr = GeminiPrescriptionOCR(api_key="test-key")

    with pytest.raises(FileNotFoundError, match="Image file not found"):
        ocr.ocr_image("data/prescriptions/does_not_exist.png")


@patch("rx_strategist.ocr.gemini_ocr.genai.Client")
def test_unsupported_image_type_raises_value_error(mock_client_cls, tmp_path):
    mock_client_cls.return_value = MagicMock()
    ocr = GeminiPrescriptionOCR(api_key="test-key")
    gif_path = tmp_path / "prescription.gif"
    gif_path.write_bytes(b"gif")

    with pytest.raises(ValueError, match="Unsupported image type"):
        ocr.ocr_image(gif_path)
