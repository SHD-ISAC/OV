#!/usr/bin/env python3
"""Select and verify the local Xray-only PassWall2 profile without editing Kconfig."""

import argparse
from pathlib import Path
import re


def profile(makefile):
    suffixes = re.findall(
        r"^\s*config PACKAGE_\$\(PKG_NAME\)_((?:INCLUDE|Basic_Core)_\w+)",
        makefile, re.MULTILINE,
    )
    if not any(s in suffixes for s in ("Basic_Core_Xray", "INCLUDE_Xray")):
        raise SystemExit("ERROR: unsupported PassWall2 core options; review upstream Kconfig")
    enabled = {"Basic_Core_Xray", "INCLUDE_Xray", "INCLUDE_V2ray_GeoIP", "INCLUDE_V2ray_GeoSite"}
    values = {f"CONFIG_PACKAGE_luci-app-passwall2_{s}": "y" if s in enabled else "n" for s in suffixes}
    for package in ("luci-app-passwall2", "xray-core", "v2ray-geoip", "v2ray-geosite"):
        values[f"CONFIG_PACKAGE_{package}"] = "y"
    for package in ("luci-app-homeproxy", "luci-app-passwall", "luci-app-nikki", "luci-app-openclash"):
        values[f"CONFIG_PACKAGE_{package}"] = "n"
    return values


UNWANTED = re.compile(
    r"^(haproxy|hysteria|naiveproxy|shadowsocks-libev|shadowsocks-rust|"
    r"shadowsocksr-libev|simple-obfs|sing-box|tuic-client|v2ray-plugin)(?:-|$)"
)
ASSIGNMENT = re.compile(r"^(CONFIG_[A-Za-z0-9_-]+)=(.*)$")
UNSET = re.compile(r"^# (CONFIG_[A-Za-z0-9_-]+) is not set$")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="check the resolved .config")
    args = parser.parse_args()
    config = Path(".config")
    values = profile(Path("package/luci-app-passwall2/Makefile").read_text())
    lines = config.read_text().splitlines()
    parsed = {}
    kept = []
    for line in lines:
        match = ASSIGNMENT.fullmatch(line) or UNSET.fullmatch(line)
        if match:
            key = match[1]
            parsed[key] = match[2] if match.re is ASSIGNMENT else "n"
            if key.startswith("CONFIG_PACKAGE_") and UNWANTED.match(key.removeprefix("CONFIG_PACKAGE_")):
                values[key] = "n"
            if key in values:
                continue
        kept.append(line)
    if args.verify:
        errors = [f"{key}: expected {value}, got {parsed.get(key, 'n')}"
                  for key, value in values.items() if parsed.get(key, "n") != value]
        if errors:
            raise SystemExit("ERROR: resolved PassWall2 profile differs:\n" + "\n".join(errors))
        print("PassWall2 profile verified: Xray + GeoIP/GeoSite; optional proxy components disabled")
    else:
        kept.extend(f"{key}=y" if value == "y" else f"# {key} is not set"
                    for key, value in sorted(values.items()))
        config.write_text("\n".join(kept) + "\n")
        print("Applied Xray-only PassWall2 profile")


if __name__ == "__main__":
    main()
