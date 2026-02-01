from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from core.app.services.diagnosis_analyzer import StockDiagnosis
from core.app.usecases.portfolio_diagnosis import PortfolioDiagnosisUseCase


@pytest.fixture
def mock_repo():
    with patch("core.app.usecases.portfolio_diagnosis.UserPortfolioRepository") as mock:
        yield mock


@pytest.fixture
def mock_driver():
    with patch("core.app.usecases.portfolio_diagnosis.CNMarketDriver") as mock:
        yield mock


@pytest.fixture
def mock_analyzer():
    with patch("core.app.usecases.portfolio_diagnosis.DiagnosisAnalyzer") as mock:
        yield mock


@pytest.fixture
def mock_formatter():
    with patch("core.app.usecases.portfolio_diagnosis.DiagnosisFormatter") as mock:
        yield mock


@pytest.fixture
def mock_ai_service():
    with patch("core.app.usecases.portfolio_diagnosis.AIAnalysisService") as mock:
        yield mock


@pytest.fixture
def mock_news_service():
    with patch("core.app.usecases.portfolio_diagnosis.get_news_search_service") as mock:
        yield mock


def test_generate_diagnosis_report(
    mock_repo, mock_driver, mock_analyzer, mock_formatter, mock_ai_service, mock_news_service
):
    # Setup mocks
    repo_instance = mock_repo.return_value
    repo_instance.list_positions_by_user.return_value = [
        {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "quantity": 100,
            "cost_price": 1000,
        }
    ]

    analyzer_instance = mock_analyzer.return_value
    overview_mock = MagicMock()
    overview_mock.total_market_value = Decimal(200000)
    overview_mock.total_profit_loss = Decimal(100000)
    overview_mock.profit_loss_ratio = Decimal(100)
    overview_mock.position_count = 1
    overview_mock.position_ratio = Decimal(50)
    analyzer_instance.calculate_overview.return_value = overview_mock

    diagnosis_mock = MagicMock(spec=StockDiagnosis)
    diagnosis_mock.stock_code = "600519"
    diagnosis_mock.stock_name = "贵州茅台"
    diagnosis_mock.rating = "看好"
    diagnosis_mock.profit_loss = Decimal(100000)
    diagnosis_mock.profit_loss_ratio = Decimal(100)
    diagnosis_mock.current_price = Decimal(2000)
    diagnosis_mock.pe_ttm = Decimal(30)
    diagnosis_mock.pb = Decimal(5)
    diagnosis_mock.rsi = Decimal(50)
    diagnosis_mock.macd_dif = Decimal(10)
    diagnosis_mock.macd_dea = Decimal(5)
    diagnosis_mock.sector = "白酒"
    diagnosis_mock.position_ratio = Decimal(50)

    analyzer_instance.analyze_stock.return_value = diagnosis_mock
    analyzer_instance.generate_risk_assessment.return_value = {
        "overall_risk": "低",
        "technical_risk": "低",
        "fundamental_risk": "低",
        "position_risk": "低",
    }
    analyzer_instance.generate_suggestions.return_value = {}

    ai_service_instance = mock_ai_service.return_value
    ai_service_instance.analyze_stock.return_value = "AI Stock Analysis"
    ai_service_instance.analyze_portfolio.return_value = "AI Portfolio Analysis"

    news_service_instance = mock_news_service.return_value
    news_service_instance.search_stock_news.return_value = []

    formatter_instance = mock_formatter.return_value
    formatter_instance.format_report.return_value = "# Report"

    # Run use case
    use_case = PortfolioDiagnosisUseCase()
    # Mock output path writing
    with patch("pathlib.Path.write_text") as mock_write:
        with patch("pathlib.Path.mkdir"):
            result = use_case.generate_diagnosis_report("test_user")

    # Verify interactions
    assert repo_instance.list_positions_by_user.called
    assert analyzer_instance.calculate_overview.called
    assert analyzer_instance.analyze_stock.called
    assert news_service_instance.search_stock_news.called
    assert ai_service_instance.analyze_stock.called
    assert ai_service_instance.analyze_portfolio.called
    assert formatter_instance.format_report.called

    # Verify AI analysis was assigned
    assert diagnosis_mock.ai_analysis == "AI Stock Analysis"
