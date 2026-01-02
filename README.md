# Reseller Commission Module

Catatan modul komisi agent untuk Odoo 18. PSAK 72 compliant - agent cuma catat komisi, bukan full transaction.

## Konsep

```
Principal (PT B) ─> Punya barang
    ├─ Customer (Toko Bibit) ─> Bayar ke PT B  
    └─ Agent (PT A) ──> Bantu jual → Dapat komisi

PT A Revenue: Komisi doang (PSAK 72)
PT B Revenue: Nilai jual penuh
```

## Quick Notes

**Setup Partner:**
- PT B → `is_principal = True`
- PT A → `is_agent = True`, `commission_rate = 10%`

**Sales Order:**
- Centang `is_agent_sale`
- Pilih agent + principal
- Commission auto calculate dari amount_untaxed × rate%

**Invoice:**
- Confirm SO → status jadi "confirmed"
- Button "Make Invoice" → bikin invoice komisi ke principal
- Invoice langsung post, nilai = komisi aja

**Contoh:**
```
SO: Rp 10.000.000, Rate: 10%
→ commission_amount: 1.000.000
→ invoice ke PT B: 1.000.000 (komisi aja)
→ PT A revenue: 1.000.000
→ PT B revenue: 10.000.000
```

## Testingg

24 tests, jalanin: `odoo-bin --test-enable -i reseller_commission`
- 8 test partner commission
- 16 test SO commission
- Coverage: full scenario PSAK 72

## Files

```
models/
  res_partner.py         → extend: is_agent, is_principal, commission_rate
  sale_order.py          → extend: agent sale tracking, invoice gen
views/
  res_partner_views.xml  → form partner + commission fields
  sale_order_views.xml   → form SO + tab Commission + button Make Invoice
tests/
  test_partner_commission.py
  test_sale_order_commission.py
```

## Fields

**res.partner:**
- `is_agent` - Boolean
- `is_principal` - Boolean  
- `commission_rate` - Float 0-100%

**sale.order:**
- `is_agent_sale` - Boolean, centang kalo agent sale
- `agent_id` - Many2one res.partner
- `principal_id` - Many2one res.partner
- `commission_rate` - Float
- `commission_amount` - Monetary, computed
- `commission_status` - Selection: draft|confirmed|invoiced|paid
- `commission_invoice_id` - Many2one account.move

## Methods

`_compute_commission()` → hitung: amount_untaxed × (rate / 100)

`action_confirm()` → validasi + set status "confirmed"

`action_create_commission_invoice()` → bikin invoice ke principal, auto post, set status "invoiced"

## Validations

- Commission rate: 0-100%
- Agent sale wajib isi: agent_id, principal_id, rate > 0
- Bikin invoice: SO confirmed, belum ada invoice

## Tech Stack

Odoo 18, Python 3.10+, depends: `sale_management`, `account`

## Catatan

- Komisi dari `amount_untaxed` (before tax)
- Invoice auto-post pas dibuat
- Support multi-agent, beda rate
- Status readonly, ubah via method
- PSAK 72 compliant 
- Tests: 24/24 pass 
