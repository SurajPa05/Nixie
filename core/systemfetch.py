import subprocess
import tomli_w
from pathlib import Path



def parse(output, split_key, index=None):
    try:
        part = output.split(split_key)[1]
        # Take only the first line, not the entire lscpu dump
        first_line = part.strip().splitlines()[0]
        return first_line.split()[index] if index is not None else first_line.strip()
    except (IndexError, AttributeError):
        return "unknown"

def run_cmd_fallback(*cmds):
    for cmd in cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    return "unknown"

def parse_interfaces(ip_output):
    interfaces = []
    for line in ip_output.splitlines():
        parts = line.split()
        try:
            name = parts[1].strip(":")
            ip   = parts[3].split("/")[0]
            interfaces.append({"name": name, "ip": ip})
        except IndexError:
            continue
    return interfaces

def fetch_system_specs():
    print("Fetching system specifications...")

    lscpu  = run_cmd_fallback(["lscpu"])
    free   = run_cmd_fallback(["free", "-h"])
    df     = run_cmd_fallback(["df", "-h", "/"])
    ip     = run_cmd_fallback(["ip", "-o", "-4", "addr", "show"])
    uname_o = run_cmd_fallback(["uname", "-o"])
    uname_v = run_cmd_fallback(["uname", "-v"])
    uname_r = run_cmd_fallback(["uname", "-r"])
    ram  = run_cmd_fallback(["free", "-h", "--si"])

    # OS detection — prefers PRETTY_NAME from /etc/os-release when available
    os_release = run_cmd_fallback(["cat", "/etc/os-release"])
    os_name = next(
        (
            line.split("=")[1].strip().strip('"')
            for line in os_release.splitlines()
            if line.startswith("PRETTY_NAME")
        ),
        "unknown"
    ) if os_release else "unknown"

    version_keys = ["VERSION_ID", "VERSION", "BUILD_ID", "VERSION_CODENAME"]
    os_version = "unknown"
    for key in version_keys:
        match = next(
            (line.split("=")[1].strip().strip('"') for line in os_release.splitlines() if line.startswith(key)),
            None
        )
        if match:
            os_version = match
            break

    # Package manager detection
    pkg_manager = run_cmd_fallback(
        ["pacman", "--version"],   # Arch
        ["apt", "--version"],      # Debian/Ubuntu
        ["dnf", "--version"],      # Fedora
        ["zypper", "--version"],   # openSUSE
        ["apk", "--version"],      # Alpine
    )

    config = {
        "hardware": {
            "cpu_model": lscpu.split("Model name:")[1].split("\n")[0].strip() if lscpu and "Model name:" in lscpu else "unknown",
            "ram_total": parse(free, "Mem:", 0) if free else "unknown",
            "disk_total": parse(df, "\n", 1) if df else "unknown",
            "network_interfaces": parse_interfaces(ip) if ip else []
        },
        "software": {
            "os_name": os_name,
            "os_version": os_version,
            "kernel_version": uname_r,
            "pkg_manager": next((line for line in pkg_manager.splitlines() if "Pacman" in line or "apt" in line or "dnf" in line),"unknown").strip(".-– ") if pkg_manager else "unknown",
        }
    }

    return config

def save_system_specs(config):
    toml_path = Path(__file__).parent.parent / "system_details.toml"
    
    # Create with empty fields if it doesn't exist
    if not toml_path.exists():
        default = {
            "hardware": {
                "cpu_model": "",
                "ram_total": "",
                "disk_total": "",
                "network_interfaces": []
            },
            "software": {
                "os_name": "",
                "os_version": "",
                "kernel_version": "",
                "pkg_manager": ""
            }
        }
        with open(toml_path, "wb") as f:
            tomli_w.dump(default, f)
        print(f"Created new config at {toml_path}")

    # Now write actual specs
    with open(toml_path, "wb") as f:
        tomli_w.dump(config, f)
    
    print(f"System specs saved to {toml_path}")

if __name__ == "__main__":
    config = fetch_system_specs()
    save_system_specs(config)