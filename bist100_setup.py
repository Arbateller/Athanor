"""
bist100_setup.py - Automatically adds all BIST100 stocks to your .env
Run from project root:
    python bist100_setup.py
"""

import os

# All BIST100 stocks as of 2026 (Yahoo Finance format with .IS suffix)
BIST100 = [
    "ACSEL.IS", "AGESA.IS", "AKBNK.IS", "AKCNS.IS", "AKFEN.IS",
    "AKGRT.IS", "AKHOL.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS",
    "ALBRK.IS", "ALFAS.IS", "ALKIM.IS", "ANACM.IS", "ANELE.IS",
    "ARCLK.IS", "ARDYZ.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS",
    "AYDEM.IS", "AYGAZ.IS", "BERA.IS", "BIMAS.IS", "BIOEN.IS",
    "BRISA.IS", "BRYAT.IS", "BTCIM.IS", "BUCIM.IS", "CCOLA.IS",
    "CEMAS.IS", "CEMTS.IS", "CIMSA.IS", "CLEBI.IS", "CORGT.IS",
    "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS",
    "EKGYO.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "EUREN.IS",
    "FENER.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS",
    "GLYHO.IS", "GOBFN.IS", "GOODY.IS", "GOZDE.IS", "GUBRF.IS",
    "GWIND.IS", "HALKB.IS", "HEKTS.IS", "HTTBT.IS", "ICBCT.IS",
    "IHLGM.IS", "ISCTR.IS", "ISDMR.IS", "ISFIN.IS", "ISGYO.IS",
    "ISYAT.IS", "IZMDC.IS", "JANTS.IS", "KARSN.IS", "KAYSE.IS",
    "KCAER.IS", "KCHOL.IS", "KLNMA.IS", "KMPUR.IS", "KONTR.IS",
    "KONYA.IS", "KOPOL.IS", "KORDS.IS", "KOZAA.IS", "KOZAL.IS",
    "KRDMD.IS", "LOGO.IS", "MAVI.IS", "MGROS.IS", "MPARK.IS",
    "NETAS.IS", "NTTUR.IS", "NUHCM.IS", "ODAS.IS", "OTKAR.IS",
    "OYAKC.IS", "PAPIL.IS", "PARSN.IS", "PEGOS.IS", "PGSUS.IS",
    "QUAGR.IS", "REEDR.IS", "SAHOL.IS", "SASA.IS", "SELEC.IS",
    "SISE.IS", "SKBNK.IS", "SMART.IS", "SMRTG.IS", "SOKM.IS",
    "SUPRS.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TIRE.IS",
    "TKFEN.IS", "TKNSA.IS", "TLMAN.IS", "TOASO.IS", "TSKB.IS",
    "TTKOM.IS", "TTRAK.IS", "TUCLK.IS", "TUPRS.IS", "TURSG.IS",
    "ULKER.IS", "USDTR.IS", "VAKBN.IS", "VERUS.IS", "VESBE.IS",
    "VESTL.IS", "VKGYO.IS", "YKBNK.IS", "YYLGD.IS", "ZRGYO.IS",
]

def update_env():
    env_path = os.path.join("config", ".env")

    if not os.path.exists(env_path):
        print(f"❌ Could not find {env_path}")
        print("Make sure you run this from the project root folder.")
        return

    # Read existing .env
    with open(env_path, "r") as f:
        lines = f.readlines()

    # Build the new TRACKED_STOCKS line
    tickers_str = ",".join(BIST100)
    new_line = f"TRACKED_STOCKS={tickers_str}\n"

    # Replace existing TRACKED_STOCKS line
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("TRACKED_STOCKS="):
            new_lines.append(new_line)
            updated = True
        else:
            new_lines.append(line)

    # If not found, append it
    if not updated:
        new_lines.append(new_line)

    # Write back
    with open(env_path, "w") as f:
        f.writelines(new_lines)

    print("=" * 50)
    print("   ✅ BIST100 Setup Complete!")
    print("=" * 50)
    print(f"   📊 {len(BIST100)} stocks added to tracking")
    print(f"   📁 Updated: {env_path}")
    print("=" * 50)
    print("\nNext steps:")
    print("  1. Restart fetcher:  cd fetcher && python fetcher.py")
    print("  2. Refresh Excel:    Right-click table → Refresh")
    print("\nNote: First fetch will take ~2 minutes for 100 stocks.")

if __name__ == "__main__":
    update_env()
