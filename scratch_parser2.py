import re

def parse_mfr_parameter(mfr, category):
    mfr = str(mfr).upper()
    
    # Very often the package size (0402, 0603, 0805, 1206) is in the MFR, we should strip it first to avoid confusing the resistance code
    for pkg in ["0201", "0402", "0603", "0805", "1206", "1210", "2010", "2512"]:
        if pkg in mfr:
            mfr = mfr.replace(pkg, "-", 1) # replace first occurrence

    if "RESISTOR" in category.upper():
        tol = ""
        if "F" in mfr: tol = "±1%"
        elif "J" in mfr: tol = "±5%"
        elif "D" in mfr: tol = "±0.5%"
        elif "B" in mfr: tol = "±0.1%"
        
        match = re.search(r'(?<![0-9])([0-9]{1,3}R[0-9]{1,2}|[0-9]{3,4})(?![0-9])', mfr)
        if match:
            code = match.group(1)
            try:
                if 'R' in code:
                    ohms = float(code.replace('R', '.'))
                else:
                    if len(code) == 3:
                        base = float(code[:2])
                        mult = int(code[2])
                    elif len(code) == 4:
                        base = float(code[:3])
                        mult = int(code[3])
                    else:
                        return ""
                    ohms = base * (10 ** mult)
                    
                res_val = ""
                if ohms >= 1_000_000:
                    res_val = f"{ohms/1_000_000:g}MΩ"
                elif ohms >= 1_000:
                    res_val = f"{ohms/1_000:g}kΩ"
                else:
                    res_val = f"{ohms:g}Ω"
                    
                if tol:
                    return f"{res_val} {tol}"
                return res_val
            except:
                pass
            
    elif "CAPACITOR" in category.upper():
        match = re.search(r'(?<![0-9])([0-9]{3})(?![0-9])', mfr)
        if match:
            code = match.group(1)
            base = float(code[:2])
            mult = int(code[2])
            pf = base * (10 ** mult)
            
            if pf >= 1_000_000:
                cap_val = f"{pf/1_000_000:g}μF"
            elif pf >= 1_000:
                cap_val = f"{pf/1_000:g}nF"
            else:
                cap_val = f"{pf:g}pF"
            
            tol = ""
            if "K" in mfr: tol = "±10%"
            elif "M" in mfr: tol = "±20%"
            elif "J" in mfr: tol = "±5%"
            elif "Z" in mfr: tol = "+80/-20%"
            
            # Voltage is harder, often ends in something like A=10V, E=25V etc
            if tol:
                return f"{cap_val} {tol}"
            return cap_val
            
    return ""

print("C2906873:", parse_mfr_parameter("FRC0402F4992TS", "Resistors"))
print("0603WAF1002T5E:", parse_mfr_parameter("0603WAF1002T5E", "Resistors"))
print("RC0402FR-07100KL:", parse_mfr_parameter("RC0402FR-07100KL", "Resistors"))
print("10k:", parse_mfr_parameter("103", "Resistors"))
print("4.7 ohm:", parse_mfr_parameter("4R7", "Resistors"))
print("100nF:", parse_mfr_parameter("CL05A104KA5NNNC", "Capacitors"))
