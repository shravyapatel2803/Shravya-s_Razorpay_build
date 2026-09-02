import sys, time, json
try:
    import httpx
except ImportError:
    print('ERROR: httpx not installed. Run: pip install httpx')
    sys.exit(1)

BASE_URL = 'http://127.0.0.1:8000'

TEST_EVENTS = [
    {
        'order_id': 'order_FLIGHT001',
        'payment_id': 'pay_FLIGHT001a',
        'amount': 1250000,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_TIMED_OUT',
        'error_description': 'Payment gateway timed out; no response from issuer bank.',
        'customer_name': 'Arjun Mehra',
        'customer_phone': '+919876543210',
        'customer_email': 'arjun.mehra@gmail.com',
        'customer_tier': 'VIP',
        'attempts_made': 0,
        'is_mandate': False,
    },
    {
        'order_id': 'order_GROC002',
        'payment_id': 'pay_GROC002a',
        'amount': 73500,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS',
        'error_description': 'Card declined due to insufficient balance.',
        'customer_name': 'Sunita Rao',
        'customer_phone': '+918765432109',
        'customer_email': 'sunita.rao@yahoo.in',
        'customer_tier': 'STANDARD',
        'attempts_made': 0,
        'is_mandate': False,
    },
    {
        'order_id': 'order_FASH003',
        'payment_id': 'pay_FASH003a',
        'amount': 349900,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_OTP_EXPIRED',
        'error_description': 'Customer did not complete OTP verification within the time limit.',
        'customer_name': 'Priya Sharma',
        'customer_phone': '+917654321098',
        'customer_email': 'priya.sharma@hotmail.com',
        'customer_tier': 'REPEAT_DROPOFF',
        'attempts_made': 1,
        'is_mandate': False,
    },
    {
        'order_id': 'order_MAXR004',
        'payment_id': 'pay_MAXR004a',
        'amount': 89900,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS',
        'error_description': 'Repeated insufficient funds - third attempt.',
        'customer_name': 'Ravi Kumar',
        'customer_phone': '+916543210987',
        'customer_email': 'ravi.kumar@outlook.com',
        'customer_tier': 'STANDARD',
        'attempts_made': 3,
        'is_mandate': False,
    },
    {
        'order_id': 'order_JEWL005',
        'payment_id': 'pay_JEWL005a',
        'amount': 7500000,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_OTP_EXPIRED',
        'error_description': '3DS authentication session expired during high-value checkout.',
        'customer_name': 'Deepa Nair',
        'customer_phone': '+915432109876',
        'customer_email': 'deepa.nair@gmail.com',
        'customer_tier': 'VIP',
        'attempts_made': 0,
        'is_mandate': False,
    },
    {
        'order_id': 'order_RISK006',
        'payment_id': 'pay_RISK006a',
        'amount': 450000,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_POSSIBLE_FRAUD',
        'error_description': 'Transaction flagged by Razorpay Shield - velocity anomaly detected.',
        'customer_name': 'Vikram Singh',
        'customer_phone': '+914321098765',
        'customer_email': 'vikram.singh@company.in',
        'customer_tier': 'STANDARD',
        'attempts_made': 0,
        'is_mandate': False,
    },
    {
        'order_id': 'order_BANK007',
        'payment_id': 'pay_BANK007a',
        'amount': 999900,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_BANK_SYSTEM_ERROR',
        'error_description': 'HDFC Bank core banking system returned 503 - intermittent outage.',
        'customer_name': 'Kavitha Reddy',
        'customer_phone': '+913210987654',
        'customer_email': 'kavitha.reddy@hdfc.co.in',
        'customer_tier': 'VIP',
        'attempts_made': 1,
        'is_mandate': False,
    },
    {
        'order_id': 'order_NACH008',
        'payment_id': 'pay_NACH008a',
        'amount': 500000,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_CARD_INSUFFICIENT_FUNDS',
        'error_description': 'Auto-debit rejected: insufficient balance in mandate account.',
        'customer_name': 'Anand Krishnan',
        'customer_phone': '+912109876543',
        'customer_email': 'anand.krishnan@gmail.com',
        'customer_tier': 'REPEAT_DROPOFF',
        'attempts_made': 0,
        'is_mandate': True,
    },
    {
        'order_id': 'order_EDTC009',
        'payment_id': 'pay_EDTC009a',
        'amount': 199900,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_TIMED_OUT',
        'error_description': 'UPI collect request timed out - payer did not respond.',
        'customer_name': 'Neha Gupta',
        'customer_phone': '+911098765432',
        'customer_email': 'neha.gupta@college.edu.in',
        'customer_tier': 'STANDARD',
        'attempts_made': 0,
        'is_mandate': False,
    },
    {
        'order_id': 'order_HOTL010',
        'payment_id': 'pay_HOTL010a',
        'amount': 2200000,
        'currency': 'INR',
        'error_code': 'BAD_REQUEST_PAYMENT_CARD_HOLDER_AUTHENTICATION_FAILED',
        'error_description': '3DS card-holder authentication failed on second attempt.',
        'customer_name': 'Rajesh Patel',
        'customer_phone': '+910987654321',
        'customer_email': 'rajesh.patel@vip.travel.in',
        'customer_tier': 'VIP',
        'attempts_made': 1,
        'is_mandate': False,
    },
]

COL_W = [14, 35, 28, 10, 14, 26]
HEADERS = ['Order ID', 'Error Code', 'AI Decision', 'Guardrail?', 'Recovered', 'Status']

def _sep():
    return '-+-'.join('-' * w for w in COL_W)

def _row(cells):
    parts = []
    for cell, w in zip(cells, COL_W):
        cell = str(cell)
        parts.append((cell[:w] if len(cell) > w else cell).ljust(w))
    return ' ' + ' | '.join(parts) + ' '

def paise_to_inr(p):
    return 'Rs.{:,.0f}'.format(p / 100)

def run():
    print()
    print('=' * 80)
    print('  RAZORPAY AI REVENUE RECOVERY ENGINE -- BATCH SIMULATION (10 SCENARIOS)')
    print('=' * 80)
    print()
    print('  Target : ' + BASE_URL)
    print('  Count  : ' + str(len(TEST_EVENTS)))
    print()
    sep = _sep()
    print('  ' + sep)
    print('  ' + _row(HEADERS))
    print('  ' + sep)

    results = []
    client = httpx.Client(timeout=60.0)

    for payload in TEST_EVENTS:
        oid = payload['order_id']
        ecode = payload['error_code']
        amt = payload['amount']
        try:
            r = client.post(BASE_URL + '/webhook/payment-failed', json=payload)
            if r.status_code == 409:
                rd = {'order_id': oid, 'ai_strategy': 'N/A(dup)', 'guardrail_overridden': False,
                      'payment_link_url': None, 'status': 'DUPLICATE', 'original_amount': amt}
            elif r.status_code == 200:
                rd = r.json()
            else:
                rd = {'order_id': oid, 'ai_strategy': 'ERR', 'guardrail_overridden': False,
                      'payment_link_url': None, 'status': 'HTTP_' + str(r.status_code),
                      'original_amount': amt}
        except httpx.ConnectError:
            print()
            print('  [ERROR] Cannot connect to ' + BASE_URL + '. Is the server running?')
            sys.exit(1)
        except Exception as e:
            rd = {'order_id': oid, 'ai_strategy': 'EXC', 'guardrail_overridden': False,
                  'payment_link_url': None, 'status': 'ERROR', 'original_amount': amt}

        results.append(rd)
        status = rd.get('status', 'UNKNOWN')
        guard = 'YES' if rd.get('guardrail_overridden') else 'no'
        rec = paise_to_inr(amt) if status == 'RECOVERED_PENDING_PAYMENT' else '--'
        short_err = ecode.replace('BAD_REQUEST_PAYMENT_', '').replace('BAD_REQUEST_', '')
        ai_dec = rd.get('ai_strategy', '--')
        print('  ' + _row([oid.replace('order_', ''), short_err, ai_dec, guard, rec, status]))
        time.sleep(0.4)

    print('  ' + sep)
    client.close()

    print()
    print('  Fetching metrics...')
    try:
        mr = httpx.get(BASE_URL + '/audit/metrics', timeout=10.0)
        m = mr.json()
    except Exception as e:
        m = {'error': str(e)}

    print()
    print('=' * 80)
    print('  FINAL METRICS SUMMARY')
    print('=' * 80)

    if 'error' not in m:
        at_risk   = m.get('total_gmv_at_risk_inr', 0)
        recovered = m.get('total_gmv_recovered_inr', 0)
        scheduled = m.get('total_gmv_scheduled_inr', 0)
        aborted   = m.get('total_gmv_aborted_inr', 0)
        overrides = m.get('guardrail_override_count', 0)
        rate      = m.get('recovery_success_rate_pct', 0.0)
        total     = m.get('total_events_processed', 0)

        print('  Total Events Processed      : ' + str(total))
        print('  Total GMV At Risk           : Rs.' + '{:,.2f}'.format(at_risk))
        print('  GMV Under Active Recovery   : Rs.' + '{:,.2f}'.format(recovered) + '  (payment links sent)')
        print('  GMV Queued for Silent Retry : Rs.' + '{:,.2f}'.format(scheduled) + '  (background retry)')
        print('  GMV Aborted (Manual Review) : Rs.' + '{:,.2f}'.format(aborted))
        print('  Guardrail Overrides         : ' + str(overrides))
        print('  Net Recovery Rate           : ' + str(rate) + '%')
        print()
        if at_risk > 0:
            net_pct = round((recovered + scheduled) / at_risk * 100, 1)
            print('  *** NET GMV RECOVERY: {:.1f}% of Rs.{:,.2f} at risk ***'.format(net_pct, at_risk))
    else:
        print('  Could not fetch metrics: ' + m['error'])

    print('=' * 80)
    print()

run()
