import pytest

from app.ingest import UploadError, parse_history, validate_rows

HEADER = "cycle,setting_1,setting_2,setting_3," + ",".join(f"sensor_{i}" for i in range(1, 22))


def row(cycle: int) -> str:
    return f"{cycle},0,0,100," + ",".join(str(500 + i) for i in range(1, 22))


def test_csv_with_header():
    rows = parse_history(f"{HEADER}\n{row(2)}\n{row(1)}\n".encode())
    assert [r["cycle"] for r in rows] == [1, 2]
    assert rows[0]["sensor_21"] == 521


def test_symbol_headers_and_optional_sensors():
    text = "cycle,Alt,Mach,TRA,T24,T30,T50,P30,Nf,Nc,Ps30,phi,NRf,NRc,BPR,htBleed,W31,W32\n"
    text += "1," + ",".join(["1"] * 17) + "\n"
    rows = parse_history(text.encode())
    assert rows[0]["sensor_4"] == 1
    assert rows[0].get("sensor_1") is None


def test_semicolon_delimited_csv():
    text = f"{HEADER}\n{row(1)}\n".replace(",", ";")
    assert len(parse_history(text.encode())) == 1


@pytest.mark.parametrize(
    "text, message",
    [
        (f"{HEADER}\n{row(1)}\n{row(1)}\n", "repeat"),
        (f"{HEADER}\n{row(0)}\n", "start at 1"),
        ("cycle,sensor_2\n1,5\n", "Missing columns"),
        (f"{HEADER}\n" + row(1).replace(",501", ",inf", 1) + "\n", "infinite"),
    ],
)
def test_rejections(text, message):
    with pytest.raises(UploadError, match=message):
        parse_history(text.encode())


def test_row_limit():
    text = HEADER + "\n" + "\n".join(row(i) for i in range(1, 12))
    with pytest.raises(UploadError, match="At most 10"):
        parse_history(text.encode(), max_rows=10)


def test_json_rows_use_the_same_rules():
    values = dict(zip(HEADER.split(","), map(float, row(1).split(","))))
    assert validate_rows([values])[0]["cycle"] == 1
    with pytest.raises(UploadError):
        validate_rows([])
