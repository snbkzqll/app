import re

def parse_resistor_mfr(mfr):
    # Try to find 3 or 4 digit resistance code
    # e.g., FRC0402F4992TS -> '4992', F = 1%
    # RC0402FR-07100KL -> '100K' or '1004'?
    # Actually it's easier: just use the mfr code.
    
    # 4-digit code (e.g. 4992, 1002, 1004)
    # usually preceded by F/J or followed by F/J
    match = re.search(r'([A-Z]*)([0-9]{3,4})([A-Z]*)', mfr)
    
    # Actually, a better way is to search for common patterns.
    # 1. 4-digit or 3-digit number where last digit is multiplier
    patterns = [
        r'(F|J)(\d{3,4})', # F4992
        r'(\d{3,4})(F|J)'  # 1002F
    ]
    
    res_val = ""
    prec = ""
    
    for p in patterns:
        m = re.search(p, mfr)
        if m:
            if "F" in m.groups() or "J" in m.groups():
                parts = m.groups()
                code = parts[1] if parts[0] in ['F', 'J'] else parts[0]
                prec = "±1%" if "F" in parts else "±5%"
                
                if len(code) == 3:
                    base = float(code[:2])
                    mult = int(code[2])
                else:
                    base = float(code[:3])
                    mult = int(code[3])
                
                ohms = base * (10 ** mult)
                
                if ohms >= 1_000_000:
                    res_val = f"{ohms/1_000_000:g}MΩ"
                elif ohms >= 1_000:
                    res_val = f"{ohms/1_000:g}kΩ"
                else:
                    res_val = f"{ohms:g}Ω"
                
                return f"{res_val} {prec}"
                
    return ""

print(parse_resistor_mfr("FRC0402F4992TS"))
print(parse_resistor_mfr("0603WAF1002T5E"))
print(parse_resistor_mfr("RC0402FR-07100KL")) # This one has 100K explicitly, my regex might fail.
