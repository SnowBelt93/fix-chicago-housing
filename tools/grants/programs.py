"""The programs the grants finder checks: python3 tools/grants/programs.py writes grants/data/programs.json.

Every program here was read on its official page (or the agency's own announcement) on the date in `checked`.
**When you change a program, change `checked` too.** Anything older than 90 days shows as "may be out of date".

Fields
  id, name, by (who runs it), for (roles: owner, buyer, renter, landlord, business, developer, nonprofit)
  goal (buy, repair, energy, tax, rent, build, storefront), form (grant, forgivable, loan, credit, tax, service, land)
  amount: short text;  max: dollars or None
  rules: checks the page runs on the answers (all must pass; a rule the visitor didn't answer counts as "maybe"):
     ["chicago"]                    address in Chicago (or no address given)
     ["ami", 80]                    household income at or below 80% of HUD's area median income for the household size
     ["age", 65]                    someone in the household this age or older (owner programs: the owner)
     ["own"]  ["units", 4]          owner lives there / building has at most 4 homes
     ["first"]                      first-time buyer
     ["layer", "tif" | "nof" | "qct" | "oz" | "hist"]   address inside that area
     ["income", 65000]              total household income at or below a dollar figure
     ["liheap"]                     the state's monthly LIHEAP income table (data.liheap)
     ["disab"] ["vet"] ["vetdis"]   someone with a disability / a veteran / a veteran with a VA disability rating
  status: [kind, note]   kind = open | rolling | seasonal | round | waitlist | closed
  link: where to apply or read the rules;  src: [[label, url], ...];  note: one line of fine print
"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
C = '2026-11-12'
P = [
 # ---------- buying a home ----------
 dict(id='homegrown', name='HomeGrown Purchase Assistance', by='City of Chicago Department of Housing', for_=['buyer'], goal=['buy'], form='grant',
      amount='Up to $70,000 toward down payment and closing costs', max=70000,
      rules=[['chicago'], ['ami', 150]],
      status=['open', 'Applications opened June 8, 2026; funds go first come, first served until they run out.'],
      link='https://www.chicago.gov/homegrown',
      src=[['Chicago Association of Realtors, June 2026', 'https://chicagorealtor.com/chicago-just-launched-a-new-down-payment-assistance-program-heres-what-your-clients-need-to-know/']],
      note='The grant depends on income and which zone the home is in (up to 150% of area median income in Zone B), may not exceed 25% of the price, and needs homebuyer counseling, 1% of the price from you and five years living there. Apply through The Resurrection Project or NHS Chicago.', checked=C),
 dict(id='dpp', name='Downpayment Plus', by='Federal Home Loan Bank of Chicago, through member banks', for_=['buyer'], goal=['buy'], form='forgivable',
      amount='Up to $10,000, forgiven over time', max=10000, rules=[['ami', 80]],
      status=['open', '2026 funding is $48 million; it runs until the money is used.'],
      link='https://www.fhlbc.com/news/details/2026/01/20/fhlbank-chicago-launches-2026-downpayment-plus--grant-programs--unlocking--28-million-to-support-homebuyers-in-illinois-and-wisconsin',
      src=[['FHLBank Chicago, Jan. 20, 2026', 'https://www.fhlbc.com/news/details/2026/01/20/fhlbank-chicago-launches-2026-downpayment-plus--grant-programs--unlocking--28-million-to-support-homebuyers-in-illinois-and-wisconsin']],
      note='Ask your lender whether it takes part. Downpayment Plus Advantage works the same way through nonprofit mortgage programs.', checked=C),
 dict(id='ihda', name='IHDA Access down payment help', by='Illinois Housing Development Authority', for_=['buyer'], goal=['buy'], form='forgivable',
      amount='$6,000 forgivable, $7,500 deferred, $10,000 repayable, or up to $15,000 for first-time buyers (Access Home)', max=15000, rules=[],
      status=['open', 'Year-round through participating lenders.'],
      link='https://www.ihdamortgage.org/',
      src=[['Illinois Realtors, June 2026', 'https://www.illinoisrealtors.org/wp-content/uploads/2026/06/NineHomeFinancingPrograms_Jun2026.pdf']],
      note='Comes with an IHDA first mortgage. Income and price limits depend on the county and household size; an IHDA lender checks them.', checked=C),
 # ---------- fixing a home ----------
 dict(id='hrp', name='Home Repair Program (roofs and porches)', by='City of Chicago Department of Housing', for_=['owner'], goal=['repair'], form='grant',
      amount='Roof or porch repair, based on an inspection', max=None, rules=[['chicago'], ['own'], ['ami', 50]],
      status=['seasonal', 'Registration opens once a year for about two weeks (it ran March 10–21, 2025). Next dates are posted on the program page.'],
      link='https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/home-repair-program.html',
      src=[['City program page', 'https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/home-repair-program.html'], ['WTTW, March 2025', 'https://news.wttw.com/2025/03/08/registration-opens-monday-chicago-s-home-repair-program-here-s-what-you-need-know']],
      note='Registering doesn\'t guarantee a repair; the city picks from the registrations by need and money available.', checked=C),
 dict(id='ehrp', name='Emergency Heating Repair Program', by='City of Chicago Department of Housing', for_=['owner'], goal=['repair'], form='grant',
      amount='Furnace or boiler repair or replacement in winter', max=None, rules=[['chicago'], ['own'], ['units', 4], ['ami', 80]],
      status=['seasonal', 'Open each winter, first come, first served (last posted window: Nov. 1, 2024 to April 1, 2025).'],
      link='https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/emergency-heating-repair-program.html',
      src=[['City program page', 'https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/emergency-heating-repair-program.html']],
      note='Your name must have been on the deed for at least a year, and utilities must be on. Sell or move out within a year and you repay part of it.', checked=C),
 dict(id='sarfs', name='Small Accessible Repairs for Seniors (SARFS)', by='City of Chicago Department of Housing', for_=['owner'], goal=['repair'], form='service',
      amount='Free grab bars, railings, door and window fixes, smoke and CO detectors', max=None, rules=[['chicago'], ['own'], ['units', 4], ['age', 60], ['ami', 80]],
      status=['closed', 'The waiting list closed Dec. 21, 2022; only people already on it are being served.'],
      link='https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/sarfs.html',
      src=[['City program page', 'https://chicago.gov/city/en/depts/doh/provdrs/homeowners/svcs/sarfs.html']],
      note='Listed so you know it exists if the list reopens.', checked=C),
 # ---------- property tax (rules only: we never look up anyone's bill) ----------
 dict(id='ex_home', name='Homeowner Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Lowers the taxable value of your home; about $950 a year on average', max=None, rules=[['own']],
      status=['open', 'Renews by itself once you have it; missed years can be claimed back.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']],
      note='For the home you live in. Check your last bill or the Assessor\'s site to see if you already get it.', checked=C),
 dict(id='ex_senior', name='Senior Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Lowers the taxable value of your home', max=None, rules=[['own'], ['age', 65]],
      status=['open', 'Renews by itself; missed years can be claimed back.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']], note='', checked=C),
 dict(id='ex_freeze', name='Senior Freeze (Low-Income Senior Assessment Freeze)', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Freezes the taxable value of your home', max=None, rules=[['own'], ['age', 65], ['income', 65000]],
      status=['open', 'File every year.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']],
      note='Total household income of $65,000 or less (the Assessor checks the year before the tax year).', checked=C),
 dict(id='ex_disab', name='Persons with Disabilities Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Lowers the taxable value of your home', max=None, rules=[['own'], ['disab']],
      status=['open', 'Renews by itself under a new state law.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']], note='', checked=C),
 dict(id='ex_vetdis', name='Veterans with Disabilities Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Lowers the taxable value of your home; the amount depends on the disability rating', max=None, rules=[['own'], ['vetdis']],
      status=['open', 'File every year.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']], note='', checked=C),
 dict(id='ex_retvet', name='Returning Veterans Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax'], form='tax',
      amount='Lowers the taxable value of your home in the year you return', max=None, rules=[['own'], ['vet']],
      status=['open', 'File for each year of return from active duty in an armed conflict.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']], note='', checked=C),
 dict(id='ex_improve', name='Home Improvement Exemption', by='Cook County Assessor', for_=['owner'], goal=['tax', 'repair'], form='tax',
      amount='Up to $75,000 of added value isn\'t taxed for four years', max=None, rules=[['own']],
      status=['open', 'Automatic: no application.'],
      link='https://cookcountyassessoril.gov/exemptions', src=[['Cook County Assessor', 'https://cookcountyassessoril.gov/exemptions']],
      note='Good to know before you add a room or a coach house.', checked=C),
 # ---------- bills and rent ----------
 dict(id='liheap', name='LIHEAP energy bill help', by='State of Illinois, through CEDA in Cook County', for_=['owner', 'renter'], goal=['energy'], form='grant',
      amount='Help with gas and electric bills, reconnection and furnace repair', max=None, rules=[['liheap']],
      status=['open', 'Oct. 1, 2026 to Aug. 13, 2027, or until the money runs out.'],
      link='https://cedaorg.net/bills',
      src=[['Illinois DCEO, Help Illinois Families', 'https://dceo.illinois.gov/communityservices/homeweatherization/communityactionagencies/helpillinoisfamilies.html']],
      note='Renters whose heat is included in rent can get cash help too. CEDA also runs free weatherization for income-eligible homes.', checked=C),
 dict(id='rap', name='Rental Assistance Program (RAP)', by='City of Chicago Department of Family and Support Services', for_=['renter'], goal=['rent'], form='grant',
      amount='Back rent, future rent or a security deposit to stop an eviction or homelessness', max=None, rules=[['chicago']],
      status=['closed', 'The online portal closed March 28 until more money comes in; Community Service Centers can still help by phone or in person.'],
      link='https://www.chicago.gov/city/en/depts/fss/provdrs/serv/svcs/homeless_prevention.html',
      src=[['City program page', 'https://www.chicago.gov/city/en/depts/fss/provdrs/serv/svcs/homeless_prevention.html']],
      note='For low-income households at risk of eviction or losing income; open regardless of immigration status.', checked=C),
 # ---------- storefronts and buildings with businesses ----------
 dict(id='sbif', name='Small Business Improvement Fund (SBIF)', by='City of Chicago Department of Planning and Development', for_=['business', 'landlord'], goal=['storefront'], form='grant',
      amount='Up to $150,000 per commercial property ($250,000 with several tenants or for industrial)', max=250000, rules=[['layer', 'tif']],
      status=['round', 'Opens one TIF district at a time for 30 days; the city announces districts monthly.'],
      link='https://www.chicago.gov/sbif',
      src=[['Department of Planning and Development, April 2026', 'https://chicagochinatown.org/wp-content/uploads/2026/04/DPD-Grant-Program-Best-Practices_11th-Ward-4.23.26-1.pdf']],
      note='Pays you back after the work for roofs, facades, mechanicals, ADA and similar. Not for homes or home businesses.', checked=C),
 dict(id='nof', name='Neighborhood Opportunity Fund', by='City of Chicago Department of Planning and Development', for_=['business', 'landlord', 'developer'], goal=['storefront', 'build'], form='grant',
      amount='Up to $250,000, covering 75% of eligible costs', max=250000, rules=[['chicago']],
      status=['rolling', 'Rolling applications, picked each quarter.'],
      link='https://www.chicago.gov/nof',
      src=[['Department of Planning and Development, April 2026', 'https://chicagochinatown.org/wp-content/uploads/2026/04/DPD-Grant-Program-Best-Practices_11th-Ward-4.23.26-1.pdf']],
      note='Only on eligible South, Southwest and West Side commercial corridors (check the city\'s map). You need to show you can pay half the project. Can pay for buying the property and new buildings on empty lots.', checked=C),
 dict(id='cdg', name='Community Development Grant', by='City of Chicago Department of Planning and Development', for_=['business', 'developer', 'nonprofit'], goal=['storefront', 'build'], form='grant',
      amount='Small: up to $250,000 (75% of costs). Medium: $300,001 to $5 million. Large: over $5 million', max=None, rules=[['chicago']],
      status=['round', 'Small grants open twice a year (the last round closed Aug. 14, 2026); large grants are rolling.'],
      link='https://chicagochinatown.org/wp-content/uploads/2026/04/DPD-Grant-Program-Best-Practices_11th-Ward-4.23.26-1.pdf',
      src=[['Department of Planning and Development, April 2026', 'https://chicagochinatown.org/wp-content/uploads/2026/04/DPD-Grant-Program-Best-Practices_11th-Ward-4.23.26-1.pdf']],
      note='Commercial, mixed-use, industrial and community buildings.', checked=C),
 # ---------- building housing ----------
 dict(id='lihtc9', name='9% Low-Income Housing Tax Credits', by='City of Chicago Department of Housing', for_=['developer', 'nonprofit'], goal=['build'], form='credit',
      amount='Up to $1.8 million a year in credits for 10 years (sold to investors for equity)', max=None, rules=[['chicago']],
      status=['round', 'One competitive round a year under the city\'s Qualified Allocation Plan, starting with a Preliminary Project Application.'],
      link='https://www.chicago.gov/city/en/depts/doh/supp_info/2025-qualified-allocation-plan.html',
      src=[['2025 Qualified Allocation Plan', 'https://www.chicago.gov/content/dam/city/depts/doh/qap/2025/2025%20QAP%20Final.pdf'], ['Underwriting Standards Guide', 'https://www.chicago.gov/content/dam/city/depts/doh/qap/2025/Underwriting%20Standards%20Guide%20Final.pdf']],
      note='Rental homes for households at or below 60% of area median income (average 57% or less with income averaging). The deal check scores your site against the plan.', checked=C),
 dict(id='lihtc4', name='4% tax credits with tax-exempt bonds', by='City of Chicago Department of Housing or IHDA', for_=['developer', 'nonprofit'], goal=['build'], form='credit',
      amount='About 4% of qualified basis a year for 10 years, not competitive', max=None, rules=[],
      status=['rolling', 'The city takes bond-only applications on a rolling basis.'],
      link='https://www.chicago.gov/city/en/depts/doh/supp_info/2025-qualified-allocation-plan.html',
      src=[['2025 Qualified Allocation Plan', 'https://www.chicago.gov/content/dam/city/depts/doh/qap/2025/2025%20QAP%20Final.pdf'], ['Nixon Peabody on the 2025 federal tax law', 'https://www.nixonpeabody.com/-/media/files/alerts/2025/07/lihtc_and_obbba.pdf']],
      note='For bonds issued after 2025, bonds must pay for at least 25% of the land and building (it was 50%).', checked=C),
 dict(id='gap', name='Multifamily gap financing', by='City of Chicago Department of Housing', for_=['developer', 'nonprofit'], goal=['build'], form='loan',
      amount='Up to 20% of total development cost at the first application', max=None, rules=[['chicago']],
      status=['round', 'Same timeline as the city\'s tax credit round.'],
      link='https://www.chicago.gov/city/en/depts/doh/supp_info/2025-qualified-allocation-plan.html',
      src=[['Underwriting Standards Guide', 'https://www.chicago.gov/content/dam/city/depts/doh/qap/2025/Underwriting%20Standards%20Guide%20Final.pdf']],
      note='Soft loan repaid from 25% of surplus cash. In 2023–24 the city put in $217,504 per home on average, counting all its sources.', checked=C),
 dict(id='ahsap', name='Affordable Housing Special Assessment Program', by='Cook County Assessor', for_=['developer', 'nonprofit', 'landlord'], goal=['build', 'tax'], form='tax',
      amount='Lower property taxes for 10 or 30 years on buildings with affordable homes', max=None, rules=[],
      status=['open', 'Part 1 before the building opens; apply by Sept. 5 to count for that tax year.'],
      link='https://www.cookcountyassessoril.gov/affordable-housing',
      src=[['Assessor FAQ', 'https://www.cookcountyassessoril.gov/frequently-asked-questions-ahsap']],
      note='Buildings of 7+ homes with 15% or 35% of homes at 60% of area median income or less, after new construction or a big rehab.', checked=C),
 dict(id='iahtc', name='Illinois Affordable Housing Tax Credit (donations)', by='City of Chicago Department of Housing (in Chicago) and IHDA', for_=['developer', 'nonprofit'], goal=['build'], form='credit',
      amount='Donors get a state tax credit worth 50% of what they give the project', max=None, rules=[],
      status=['round', 'Applied for with the city\'s housing funding.'],
      link='https://www.ihda.org/developers/tax-credits/illinois-affordable-housing-tax-credit/',
      src=[['IHDA program page', 'https://www.ihda.org/developers/tax-credits/illinois-affordable-housing-tax-credit/']],
      note='For nonprofit sponsors. Rentals: at least 25% of homes at 60% of area median income or less.', checked=C),
 dict(id='ahp', name='Affordable Housing Program (AHP)', by='Federal Home Loan Bank of Chicago, with a member bank', for_=['developer', 'nonprofit'], goal=['build'], form='grant',
      amount='Up to $2 million a project', max=2000000, rules=[],
      status=['round', 'One round a year; 2026 applications were due June 12, 2026.'],
      link='https://fhlbc.com/AHP',
      src=[['FHLBank Chicago, May 4, 2026', 'https://www.fhlbc.com/news/news-detail/2026/05/04/fhlbank-chicago-opens-2026-affordable-housing-program-with--51-million-available']],
      note='Competitive. Apply jointly with a member bank.', checked=C),
 dict(id='ilhtc', name='Illinois Historic Preservation Tax Credit', by='Illinois State Historic Preservation Office', for_=['developer', 'landlord'], goal=['build', 'repair'], form='credit',
      amount='25% of rehab costs, up to $3 million a project', max=3000000, rules=[['layer', 'hist']],
      status=['round', 'Two rounds a year; the state hands out $25 million a year.'],
      link='https://dnrhistoric.illinois.gov/preserve/statecredit.html',
      src=[['State Historic Preservation Office', 'https://dnrhistoric.illinois.gov/preserve/statecredit.html']],
      note='Buildings on the National Register (or in a listed district) that earn income after the rehab. Pairs with the 20% federal historic credit.', checked=C),
 dict(id='oz', name='Opportunity Zone', by='U.S. Treasury (federal tax law)', for_=['developer'], goal=['build'], form='tax',
      amount='Investors who put capital gains into new building here can cut their federal taxes', max=None, rules=[['layer', 'oz']],
      status=['open', 'The 2018 map runs through 2028; a new map takes effect Jan. 1, 2027.'],
      link='https://www.crowe.com/insights/tax-news-highlights/obbba-makes-enhanced-opportunity-zones-permanent',
      src=[['Crowe on the 2025 federal tax law', 'https://www.crowe.com/insights/tax-news-highlights/obbba-makes-enhanced-opportunity-zones-permanent']],
      note='Brings equity, not a grant. Works best with market-rate or mixed-income buildings.', checked=C),
 dict(id='missing', name='Missing Middle Infill Housing Initiative', by='City of Chicago Department of Planning and Development', for_=['developer'], goal=['build'], form='land',
      amount='City lots for $1 plus up to $150,000 a home in construction help', max=150000, rules=[['chicago']],
      status=['round', 'Rounds by neighborhood (so far North Lawndale; then Chatham, South Chicago and Morgan Park). Applications go through ChiBlockBuilder.'],
      link='https://www.chicago.gov/missingmiddle',
      src=[['City program page', 'https://www.chicago.gov/missingmiddle']],
      note='Homes are sold at market prices to people who will live in them.', checked=C),
]
out = []
for p in P:
    p = dict(p); p['for'] = p.pop('for_'); out.append(p)
LIHEAP = {'note': '30-day gross household income, program year 2026-27', 'src': 'https://dceo.illinois.gov/communityservices/homeweatherization/communityactionagencies/helpillinoisfamilies.html',
          'by': [3990, 5410, 6830, 8250, 9670, 11090]}
json.dump({'checked': C, 'programs': out, 'liheap': LIHEAP}, open(os.path.join(ROOT, 'grants', 'data', 'programs.json'), 'w'), indent=1, ensure_ascii=False)
print(len(out), 'programs')
