# Companies report (2026-09-13)

- Candidates considered: 261 (15 already verified before this pass, 246 new names)
- Resolved to a Workday slug from search-result URLs: 155
- Verified (empty search returned `total`): 147 new, 162 total in companies.json
- Failed verification twice and dropped: 8
- Not on Workday: 97 (see `not_on_workday.json`; 58 of them got only one search because the session's web-search budget ran out)

## Not on Workday, by ATS seen

- own: 70
- Workday: 8
- Greenhouse: 4
- Oracle: 3
- SmartRecruiters: 2
- only: 2
- Brassring: 2
- Lever: 2
- now: 1
- SuccessFactors: 1
- Taleo: 1
- Workable: 1

## Estimated run time

- Per search: pages x 1.6 s; pages per tier: {1: 3, 2: 2, 3: 1}; 4 search terms per company
- Daily (tier 1 + 2, 124 companies): about 32 min for the search phase, plus roughly 2 s per new posting for detail fetches and 8 s per scored posting
- Tier 3 days (Mon/Thu, +38 companies): about 36 min
- Cache hits (same day reruns) cost nothing.

## Tier 1 (47)

| Company | Tenant | Site | Open roles | sponsors_h1b | Source |
|---|---|---|---|---|---|
| Adobe | adobe.wd5 | external_experienced | 739 | True | seeded by hand (round 2) |
| Ally | ally.wd1 | Ally | 89 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Autodesk | autodesk.wd1 | Ext | 403 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| BlackRock | blackrock.wd1 | BlackRock_Professional | 316 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Booking | priceline.wd1 | BookingHoldings | 23 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Broadcom | broadcom.wd1 | External_Career | 369 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| CVS Health | cvshealth.wd1 | CVS_Health_Careers | 18150 | True | seeded by hand (round 2) |
| Cardinal Health | cardinalhealth.wd1 | EXT | 783 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Cigna | cigna.wd5 | cignacareers | 560 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Cisco | cisco.wd5 | Cisco_Careers | 1323 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Citi | citi.wd5 | 2 | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| CrowdStrike | crowdstrike.wd5 | crowdstrikecareers | 394 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Elevance | elevancehealth.wd1 | ANT | 292 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Expedia | expedia.wd108 | search | 154 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| FactSet | factset.wd108 | FactSetCareers | 69 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Fannie Mae | fanniemae.wd1 | FannieMaeCareers | 61 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Fidelity | fmr.wd1 | FidelityCareers | 633 | True | seeded by hand (round 2) |
| Freddie Mac | freddiemac.wd5 | External | 104 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Humana | humana.wd5 | Humana_External_Career_Site | 364 | True | seeded by hand (round 2) |
| IQVIA | iqvia.wd1 | IQVIA | 1917 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Intel | intel.wd1 | External | 590 | True | seeded by hand (round 2) |
| KLA | kla.wd1 | Search | 997 | True | seeded by hand (round 2) |
| LexisNexis | relx.wd3 | RiskSolutions | 172 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Marvell | marvell.wd1 | MarvellCareers | 170 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Mastercard | mastercard.wd1 | CorporateCareers | 1040 | True | seeded by hand (round 2) |
| McKesson | mckesson.wd3 | External_Careers | 497 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Medline | medline.wd5 | Medline | 587 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Micron | micron.wd1 | External | 2916 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Morgan Stanley | ms.wd5 | External | 1284 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| NVIDIA | nvidia.wd5 | NVIDIAExternalCareerSite | 2000 | True | seeded by hand (round 2) |
| Nasdaq | nasdaq.wd1 | Global_External_Site | 176 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Netflix | netflix.wd108 | Netflix | 646 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| PayPal | paypal.wd1 | jobs | 132 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Proofpoint | proofpoint.wd5 | ProofpointCareers | 146 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| S&P Global | spgi.wd5 | SPGI_Careers | 299 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Salesforce | salesforce.wd12 | External_Career_Site | 1442 | True | seeded by hand (round 2) |
| Snap | snapchat.wd1 | snap | 174 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| State Street | statestreet.wd1 | Global | 1217 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Synchrony | synchronyfinancial.wd5 | careers | 37 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| T. Rowe Price | troweprice.wd5 | TRowePrice | 135 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| TIAA | tiaa.wd1 | Search | 237 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Thomson Reuters | thomsonreuters.wd5 | External_Career_Site | 442 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Truist | truist.wd1 | Careers | 1115 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Vanguard | vanguard.wd5 | vanguard_external | 440 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Visa | visa.wd5 | Visa | 760 | True | seeded by hand (round 2) |
| Workday | workday.wd5 | Workday | 391 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Zoom | zoom.wd5 | Zoom | 86 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |

## Tier 2 (77)

| Company | Tenant | Site | Open roles | sponsors_h1b | Source |
|---|---|---|---|---|---|
| 3M | 3m.wd1 | Search | 666 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| AIG | aig.wd1 | aig | 507 | True | FY2025 LCA lookup: 66 LCAs across AIG PC Global Services (47) and AIG Employee Services (19) |
| ASML | asml.wd3 | ASMLEXT1 | 607 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| AT&T | att.wd1 | ATTGeneral | 1218 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Abbott | abbott.wd5 | abbottcareers | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Accenture | accenture.wd103 | AccentureCareers | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Allstate | allstate.wd5 | allstate_careers | 477 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Altera | altera.wd1 | Altera | 218 | True | FY2025 LCA lookup: 67 LCAs |
| Amgen | amgen.wd1 | careers | 1782 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Analog Devices | analogdevices.wd1 | External | 805 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Applied Materials | amat.wd1 | External | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Baker Tilly | bakertilly.wd5 | BTCareers | 465 | True | FY2025 LCA lookup: 33 LCAs per Ellis, 7 per MyVisaJobs |
| Bank of America | ghr.wd1 | Lateral-US | 2001 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Barclays | barclays.wd3 | External_Career_Site_Barclays | 994 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Bristol Myers Squibb | bristolmyerssquibb.wd5 | BMS | 611 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| CareSource | caresource.wd1 | caresource | 122 | True | FY2025 LCA lookup: 30 LCAs |
| Caterpillar | cat.wd5 | CaterpillarCareers | 898 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Chubb | ace.wd5 | careers | 473 | True | FY2025 LCA lookup: 116 LCAs |
| Comcast | comcast.wd115 | Comcast_Careers | 676 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Credit Acceptance | creditacceptance.wd5 | credit_acceptance | 44 | True | FY2025 LCA lookup: 46 H-1B petitions approved |
| Crowe | crowe.wd12 | External_Careers | 182 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| DXC Technology | dxctechnology.wd1 | DXCJobs | 986 | True | FY2025 LCA lookup: 51 to 90 LCAs depending on source |
| Deutsche Bank | db.wd3 | DBWebsite | 1129 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Disney | disney.wd5 | disneycareer | 620 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Evolent | evolent.wd1 | External | 25 | True | FY2025 LCA lookup: 75 LCAs and LCs over FY2022 to 2024; FY2025 count not retrieved |
| F5 | ffive.wd5 | f5jobs | 208 | True | FY2025 LCA lookup: 156 LCAs |
| FedEx | fedex.wd1 | FCC_External | 2 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| GM | generalmotors.wd5 | Careers_GM | 825 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Geico | geico.wd1 | External | 283 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Genpact | genpact.wd108 | External_Careers | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Guardian Life | guardianlife.wd5 | Guardian-Life-Careers | 157 | True | FY2025 LCA lookup: 15 to 63 LCAs depending on source |
| Guidehouse | guidehouse.wd1 | External | 744 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Guidewire | guidewire.wd5 | external | 124 | True | FY2025 LCA lookup: 80 LCAs |
| HHMI | hhmi.wd1 | External | 47 | True | FY2025 LCA lookup: 160 LCAs |
| HP | hp.wd5 | ExternalCareerSite | 844 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| HPE | hpe.wd5 | Jobsathpe | 1161 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Healthfirst | healthfirst.wd1 | healthfirst | 96 | True | FY2025 LCA lookup: 28 to 35 LCAs as HF Management Services |
| Highmark Health | highmarkhealth.wd1 | highmark | 1908 | True | FY2025 LCA lookup: 27 LCAs in the first three quarters |
| Home Depot | homedepot.wd5 | CareerDepot | 1076 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Infosys | infosys.wd103 | Simplus_Careers | 14 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| JLL | jll.wd1 | jllcareers | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| LiveRamp | liveramp.wd5 | LiveRampCareers | 45 | True | FY2025 LCA lookup: 35 LCAs |
| Lowe's | lowes.wd5 | LWS_External_CS | 12389 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Manulife John Hancock | manulife.wd3 | MFCJH_Jobs | 675 | True | FY2025 LCA lookup: 43 LCAs as John Hancock Life Insurance |
| Medtronic | medtronic.wd1 | MedtronicCareers | 1140 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Merck | msd.wd5 | SearchJobs | 1151 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| NASA JPL | citjpl.wd5 | Jobs | 72 | True | FY2025 LCA lookup: 58 H-1B petitions as Caltech/JPL; many roles still carry US-person restrictions in the posting |
| NXP | nxp.wd3 | careers | 797 | True | FY2025 LCA lookup: 311 LCAs and LCs |
| Nationwide | nationwide.wd1 | Nationwide_Career | 182 | True | FY2025 LCA lookup: 54 LCAs |
| Neurocrine | neurocrine.wd5 | Neurocrinecareers | 151 | True | FY2025 LCA lookup: 16 LCAs |
| Nike | nike.wd1 | nke | 775 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| PNC | pnc.wd5 | External | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| PRA Group | pra.wd1 | PRA_Careers | 16 | True | FY2025 LCA lookup: 14 LCAs in the first three quarters; data engineer and data scientist titles |
| Pfizer | pfizer.wd1 | PfizerCareers | 574 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Prudential | pru.wd5 | Careers | 174 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| PwC | pwc.wd3 | US_Experienced_Careers | 473 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Q2 | q2ebanking.wd5 | Q2 | 47 | True | FY2025 LCA lookup: 18 LCAs |
| Royal Bank of Canada | rbc.wd3 | RBCGLOBAL1 | 1395 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| SHI International | shi.wd12 | shicareers | 231 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Samsung | sec.wd3 | Samsung_Careers | 692 | True | FY2025 LCA lookup: hundreds across Samsung Semiconductor, Research America and SDS America |
| Sanofi | sanofi.wd3 | SanofiCareers | 834 | True | FY2025 LCA lookup: 101 LCAs as Sanofi US Services |
| Strategic Education | strayer.wd1 | SEI | 26 | True | FY2025 LCA lookup: 27 LCAs and LCs; 15 petitions |
| Synechron | synechron.wd1 | SynechronCareers | 191 | True | FY2025 LCA lookup: 498 LCAs; H-1B dependent employer |
| T-Mobile | tmobile.wd1 | External | 2000 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| TD Bank | td.wd3 | TD_Bank_Careers | 1796 | True | FY2025 LCA lookup: 110 LCAs and LCs; 51 petitions |
| Target | target.wd5 | targetcareers | 2000 | True | seeded by hand (round 2) |
| Thermo Fisher | thermofisher.wd5 | thermofishercareers | 2897 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Toyota | toyota.wd503 | TMNA | 105 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| TransUnion | transunion.wd5 | TransUnion | 235 | True | FY2025 LCA lookup: FY2025 filings listed for TransUnion LLC; count not retrieved |
| Travelers | travelers.wd5 | External | 344 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| US Bank | usbank.wd1 | US_Bank_Careers | 1298 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Walmart | walmart.wd504 | WalmartExternal | 2000 | True | seeded by hand (round 2) |
| Warner Bros Discovery | warnerbros.wd5 | global | 333 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Wells Fargo | wf.wd1 | WellsFargoJobs | 1733 | True | top H-1B sponsor lists (careernomics FY2025 top-100, scoutify) |
| Yahoo | ouryahoo.wd5 | careers | 109 | True | FY2025 LCA lookup: 329 LCAs as Yahoo Holdings |
| Zendesk | zendesk.wd1 | zendesk | 110 | True | FY2025 LCA lookup: 36 LCAs |
| Zillow | zillow.wd5 | Zillow_Group_External | 107 | True | FY2025 LCA lookup: 83 LCAs |

## Tier 3 (38)

| Company | Tenant | Site | Open roles | sponsors_h1b | Source |
|---|---|---|---|---|---|
| A+E Networks | aenetworks.wd1 | AE-Careers | 14 | None | FY2025 LCA lookup: 7 LCAs |
| BD | bdx.wd1 | EXTERNAL_CAREER_SITE_USA | 631 | None | FY2025 LCA lookup: 0 found for FY2025 against 140 in FY2024; likely an entity-name mismatch, left unknown |
| BMO | bmo.wd3 | Privileged | 74 | None | not found in H-1B lists |
| Barry-Wehmiller | barrywehmiller.wd1 | BWCareers | 405 | None | not found in H-1B lists |
| Boeing | boeing.wd1 | EXTERNAL_CAREERS | 724 | False | defense contractor / postings say no sponsorship |
| Booz Allen | bah.wd1 | BAH_Jobs | 2000 | False | defense contractor / postings say no sponsorship |
| Brown & Brown | bbinsurance.wd1 | careers | 286 | None | FY2025 LCA lookup: 1 LCA |
| CACI | caci.wd1 | External | 1866 | False | defense contractor / postings say no sponsorship |
| CSI | csiweb.wd1 | CSI_Careers | 23 | None | FY2025 LCA lookup: 7 LCAs |
| Campbell's | campbellsoup.wd5 | ExternalCareers_GlobalSite | 316 | None | FY2025 LCA lookup: 5 to 13 LCAs depending on source |
| Capital One | capitalone.wd12 | Capital_One | 1939 | False | defense contractor / postings say no sponsorship |
| Cencora | myhrabc.wd5 | global | 975 | None | FY2025 LCA lookup: 2 LCAs |
| DLA Piper | dlapiper.wd1 | dlapiper | 138 | None | not found in H-1B lists |
| DTN | dtn.wd1 | DTN_Careers | 24 | None | FY2025 LCA lookup: 1 LCA |
| Deluxe | deluxe.wd5 | USA_CAN | 66 | None | FY2025 LCA lookup: 125 historical; FY2025 count not retrieved |
| Esko (Veralto) | veralto.wd1 | EskoJobs | 35 | None | FY2025 LCA lookup: no record found |
| FICO | fico.wd1 | External | 84 | None | FY2025 LCA lookup: 6 LCAs in FY2026; FY2025 count not retrieved |
| Federal Reserve Bank of NY | rb.wd5 | FRS | 138 | None | not found in H-1B lists |
| GDIT | gdit.wd5 | External_Career_Site | 1217 | False | defense contractor / postings say no sponsorship |
| GE | geaerospace.wd5 | GE_ExternalSite | 502 | False | defense contractor / postings say no sponsorship |
| GE Healthcare | gehc.wd5 | GEHC_ExternalSite | 989 | None | not found in H-1B lists |
| Hagerty | hagerty.wd5 | hagerty | 20 | False | FY2025 LCA lookup: 0 LCAs in FY2025 |
| Itron | itron.wd5 | Itron | 59 | None | FY2025 LCA lookup: 69 historical; FY2025 count not retrieved |
| J.D. Power | jdpa.wd501 | jdpower | 28 | None | FY2025 LCA lookup: 10 LCAs and LCs; 4 petitions |
| Leidos | leidos.wd5 | External | 2000 | False | defense contractor / postings say no sponsorship |
| Mimecast | mimecast.wd5 | Mimecast-Careers | 80 | None | FY2025 LCA lookup: 3 LCAs |
| Northeastern University | northeastern.wd1 | careers | 384 | None | not found in H-1B lists |
| Northrop Grumman | ngc.wd1 | Northrop_Grumman_External_Site | 3751 | False | defense contractor / postings say no sponsorship |
| Pax8 | pax8inc.wd12 | Pax8Careers | 50 | None | not found in H-1B lists |
| Pluralsight | pluralsight.wd1 | Careers | 15 | None | FY2025 LCA lookup: no record found |
| Premier Inc | premierinc.wd1 | External_Professional | 30 | None | not found in H-1B lists |
| ProMach | promachbuilt.wd108 | promach | 251 | False | FY2025 LCA lookup: no filings FY2022 through FY2025 |
| Procter & Gamble | pg.wd5 | 1000 | 788 | None | FY2025 LCA lookup: 7 LCAs |
| Raytheon | globalhr.wd5 | REC_RTX_Ext_Gateway | 4685 | False | defense contractor / postings say no sponsorship |
| Risepoint | risepoint.wd503 | risepoint | 23 | None | FY2025 LCA lookup: 1 to 2 LCAs |
| Siemens Healthineers | onehealthineers.wd3 | SHSJB | 464 | None | not found in H-1B lists |
| University of Chicago | uchicago.wd5 | External | 411 | None | not found in H-1B lists |
| WellSky | wellsky.wd1 | WellSkyCareers | 51 | None | not found in H-1B lists |
