def read_csv(file_path):
    """Read a csv file (manually, no pandas lol)"""
    dta = []
    with open(file_path, 'r') as fl:
        hdrs = [h.strip() for h in fl.readline().split(',')]
        for ln in fl:
            # Trying to catch quoted strings with commas
            vals = []
            quote_open = False
            temp = []
            for ch in ln.strip():
                if ch == '"':
                    quote_open = not quote_open
                elif ch == ',' and not quote_open:
                    vals.append(''.join(temp).strip())
                    temp = []
                else:
                    temp.append(ch)
            vals.append(''.join(temp).strip())

            if len(vals) == len(hdrs):
                dta.append(dict(zip(hdrs, vals)))
    return dta

def clean_data(d):
    """cleanup and fix data types"""
    fixd = []
    for r in d:
        fixed_row = {}
        for k, v in r.items():
            if not v or v.lower() in ('', 'na', 'null', 'none', 'n/a'):
                fixed_row[k] = None
            elif k in ['CLAIM_AMOUNT', 'PREMIUM_COLLECTED', 'PAID_AMOUNT']:
                try:
                    fixed_row[k] = float(v) if '.' in v else int(v)
                except:
                    fixed_row[k] = None
            elif k == 'CITY' and v:
                fixed_row[k] = v.strip().title()
            else:
                fixed_row[k] = v.strip()
        
        # payment status calc
        amt_paid = fixed_row.get('PAID_AMOUNT', 0) or 0
        if amt_paid == 0 and fixed_row.get('REJECTION_REMARKS'):
            fixed_row['PAYMENT_STATUS'] = 'Rejected'
        else:
            fixed_row['PAYMENT_STATUS'] = 'Paid' if amt_paid > 0 else 'Pending'
        
        fixd.append(fixed_row)
    return fixd

def classify_rejection(remark):
    """Rough classification for rejections"""
    if not remark or not isinstance(remark, str):
        return "No Remark"

    rem = remark.lower()
    if "fake document" in rem or "fake_document" in rem:
        return "Fake_document"
    elif "not covered" in rem or "not_covered" in rem:
        return "Not_Covered"
    elif "policy expired" in rem or "policy_expired" in rem:
        return "Policy_expired"
    elif "reject" in rem or "denied" in rem:
        return "Unknown"
    else:
        return "No Remark"

def add_rej_class(data):
    """Adds class to rejection"""
    for rw in data:
        rw['REJECTION_CLASS'] = classify_rejection(rw.get('REJECTION_REMARKS'))
    return data

def city_analysis(data):
    """City-wise performance stats"""
    cities = ['Pune', 'Kolkata', 'Ranchi', 'Guwahati']
    stats = {}

    for ent in data:
        cty = ent.get('CITY')
        if cty not in cities:
            continue
        
        if cty not in stats:
            stats[cty] = {
                'claims': 0,
                'claim_amt': 0,
                'premium': 0,
                'rej': 0,
                'paid': 0
            }

        stats[cty]['claims'] += 1
        stats[cty]['claim_amt'] += ent.get('CLAIM_AMOUNT', 0) or 0
        stats[cty]['premium'] += ent.get('PREMIUM_COLLECTED', 0) or 0
        stats[cty]['paid'] += ent.get('PAID_AMOUNT', 0) or 0

        if ent.get('PAYMENT_STATUS') == 'Rejected':
            stats[cty]['rej'] += 1

    worst = None
    worst_score = -999

    for c, s in stats.items():
        rej_rate = (s['rej'] / s['claims']) * 100 if s['claims'] else 0
        cl_ratio = s['claim_amt'] / s['premium'] if s['premium'] else 0
        loss = (s['paid'] / s['premium']) * 100 if s['premium'] else 0

        sc = rej_rate * 0.6 + cl_ratio * 0.4
        if sc > worst_score:
            worst_score = sc
            worst = c

    return worst, stats

def main():
    print("Reading file... hope it's there!")
    raw = read_csv('Insurance_auto_data.csv')
    clean = clean_data(raw)
    classif = add_rej_class(clean)

    # Analyzing cities
    city_to_close, citystat = city_analysis(classif)

    print("\nCity Report (April 2025-ish):")
    print("{:<10} {:<12} {:<12} {:<15} {:<15} {:<10}".format(
        "City", "Claims", "Rejected", "Rejection %", "Claim/Premium", "Loss %"))

    for c in ['Pune', 'Kolkata', 'Ranchi', 'Guwahati']:
        if c in citystat:
            s = citystat[c]
            rejpct = (s['rej'] / s['claims']) * 100
            cl2pr = s['claim_amt'] / s['premium'] if s['premium'] else 0
            lossr = (s['paid'] / s['premium']) * 100 if s['premium'] else 0

            print("{:<10} {:<12} {:<12} {:<15.2f}% {:<15.2f} {:<10.2f}%".format(
                c, s['claims'], s['rej'], rejpct, cl2pr, lossr))

    print(f"\n-> Suggest closing: {city_to_close}")

    # Reasons
    reasons = {}
    for r in classif:
        rc = r['REJECTION_CLASS']
        reasons[rc] = reasons.get(rc, 0) + 1

    print("\nRejection Reasons:")
    for reason, count in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"{reason}: {count} cases")

    # Save data?
    save = input("\nSave cleaned file? (y/n): ").lower()
    if save == 'y':
        with open('Cleaned_Insurance_Data.csv', 'w') as f:
            hdrs = classif[0].keys()
            f.write(','.join(hdrs) + '\n')
            for row in classif:
                vals = [str(v) if v is not None else '' for v in row.values()]
                f.write(','.join(vals) + '\n')
        print("Saved as Cleaned_Insurance_Data.csv")

if __name__ == '__main__':
    main()
