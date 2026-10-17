"""Independent limiting-case and accounting checks; not empirical cost validation."""
import copy
import json
import unittest
from cost_model import annuity, evaluate, installed_package, load_inputs, export_results, RESULTS


class CostChecks(unittest.TestCase):
    def test_annuity_zero_and_loan_balance(self):
        self.assertEqual(annuity(0,20),.05)
        balance=1000; payment=balance*annuity(.10,10)
        for _ in range(10):
            balance=balance*1.10-payment
        self.assertAlmostEqual(balance,0,places=8)

    def test_installed_network_excluded_from_equipment_markups(self):
        p=evaluate()['parameters']
        item=dict(cost=100,imported=0,transport_eligible=0,labour_eligible=0)
        pkg=installed_package([item],p,initial=True)
        self.assertEqual(pkg['international_freight'],0)
        self.assertEqual(pkg['inland_logistics'],0)
        self.assertEqual(pkg['installation_labour'],0)
        self.assertEqual(pkg['assumed_tax'],0)
        self.assertAlmostEqual(sum(pkg.values()),100*1.08*1.10)

    def test_replacements_and_residual_hand_calculation(self):
        inputs=copy.deepcopy(load_inputs()); components,parameters,designs,quantities=inputs
        # Independent toy: one USD100 asset, 5-year life, no other costs or generation.
        components['pv_module'].update(base_USD=100,life_years=5,annual_om_fraction=0)
        quantities['standalone']={'pv_module':1}
        p={k:0 for k in parameters}
        p.update(horizon_years=10,battery_life_years=5,loan_tenor_years=5,collection_fraction=1)
        out=evaluate('standalone',overrides=p,inputs=inputs)
        self.assertEqual(out['summary']['lifecycle_NPC_USD'],200)
        self.assertEqual([r['year'] for r in out['ledger'] if r['kind']=='replacement'],[5])
        p.update(horizon_years=8,salvage_fraction=1)
        out=evaluate('standalone',overrides=p,inputs=inputs)
        self.assertEqual(out['summary']['lifecycle_NPC_USD'],160)  # 100+100-2/5*100
        p.update(real_discount_rate=.10)
        out=evaluate('standalone',overrides=p,inputs=inputs)
        self.assertAlmostEqual(out['summary']['lifecycle_NPC_USD'],100+100/1.1**5-40/1.1**8)

    def test_all_cases_reconcile(self):
        for output in export_results():
            s=output['summary']; ledger=output['ledger']
            self.assertAlmostEqual(sum(output['initial'].values()),s['initial_budget_USD'])
            self.assertAlmostEqual(s['debt_USD']+s['equity_USD']+s['grant_USD'],s['initial_budget_USD'])
            self.assertAlmostEqual(sum(r['discounted_cost_USD'] for r in ledger),s['lifecycle_NPC_USD'])
            discounted_energy=sum(s['target_delivered_kWh_year']/(1+s['real_discount_rate'])**t
                                  for t in range(1,int(s['horizon_years'])+1))
            self.assertAlmostEqual(s['lifecycle_NPC_USD']/discounted_energy,s['conditional_USD_per_target_kWh'])
            self.assertEqual(s['adequacy_status'],'not_checked')

    def test_grid_energy_includes_losses(self):
        s=evaluate('grid_extension')['summary']
        self.assertAlmostEqual(s['grid_purchase_kWh_year'],36500/.9)
        self.assertEqual(s['diesel_litres_year'],0)

    def test_fuel_dimensions(self):
        s=evaluate('mini_grid')['summary']
        self.assertAlmostEqual(s['diesel_litres_year'],36500/.92*.1*.32)

    def test_monotonic_distance_and_fuel(self):
        near=evaluate('grid_extension',quantity_overrides={'mv_line':1})['summary']
        far=evaluate('grid_extension',quantity_overrides={'mv_line':10})['summary']
        self.assertGreater(far['initial_budget_USD'],near['initial_budget_USD'])
        a=evaluate('mini_grid',overrides={'diesel_delivered_price':1})['summary']
        b=evaluate('mini_grid',overrides={'diesel_delivered_price':3})['summary']
        self.assertEqual(a['initial_budget_USD'],b['initial_budget_USD'])
        self.assertGreater(b['lifecycle_NPC_USD'],a['lifecycle_NPC_USD'])

    def test_finance_not_double_counted_and_no_grant_in_resource_cost(self):
        a=evaluate(overrides={'debt_share':0})['summary']
        b=evaluate(overrides={'debt_share':.7})['summary']
        c=evaluate(overrides={'debt_share':0,'grant_share':.5})['summary']
        self.assertEqual(a['lifecycle_NPC_USD'],b['lifecycle_NPC_USD'])
        self.assertEqual(a['lifecycle_NPC_USD'],c['lifecycle_NPC_USD'])
        self.assertGreater(b['annual_debt_service_USD'],a['annual_debt_service_USD'])
        self.assertLess(c['equity_USD'],a['equity_USD'])

    def test_invalid_inputs_rejected(self):
        for kwargs in [dict(overrides={'collection_fraction':0}),dict(overrides={'debt_share':.8,'grant_share':.4}),
                       dict(overrides={'battery_life_years':0}),dict(quantity_overrides={'battery':-1}),
                       dict(design_overrides={'distribution_loss_fraction':1}),
                       dict(quantity_overrides={'unknown':1}),dict(overrides={'bulk_grid_supply':float('nan')})]:
            with self.assertRaises(ValueError):
                evaluate(**kwargs)
        with self.assertRaises(ValueError):
            evaluate('standalone',quantity_overrides={'pv_inverter':1})


if __name__ == '__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CostChecks))
    RESULTS.mkdir(parents=True,exist_ok=True)
    report=dict(checks_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),
                passed=result.wasSuccessful(),scope='Accounting, dimensions and limiting cases; not independent validation of costs or feasibility')
    (RESULTS/'validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(0 if result.wasSuccessful() else 1)
