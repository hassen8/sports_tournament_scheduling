import json
from pathlib import Path
import minizinc
import contextlib
import io
import pprint
from datetime import timedelta
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('-n', type=int, help="select the number of teams", default=0)

args = parser.parse_args()

BASE_DIR = Path(__file__).parent

print(BASE_DIR)


if args.n==0:
    N_VALUE = [6,8,10,12,14,16]
else:
    N_VALUE = [int(args.n)]


OUTPUT_DIR = Path(f'{BASE_DIR.parent.parent}/res/CP')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAMES = {
    "gecode_reg" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'gecode', 'opt':False, 'use_ss':0  },
    "gecode_sb" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'gecode', 'opt':False, 'use_ss':0  },
    "gecode_opt_reg" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'gecode', 'opt':True, 'use_ss':0  },
    "gecode_opt_sb" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'gecode', 'opt':True, 'use_ss':0  },
    "chuffed_reg" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'chuffed', 'opt':False, 'use_ss':0  },
    "chuffed_sb" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'chuffed', 'opt':False, 'use_ss':0  },
    "chuffed_opt_reg" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'chuffed', 'opt':True, 'use_ss':0  },
    "chuffed_opt_sb" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'chuffed', 'opt':True, 'use_ss':0  },
    "cp_reg" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'cp', 'opt':False, 'use_ss':0  },
    "cp_sb" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'cp', 'opt':False, 'use_ss':0  },
    "cp_opt_reg" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'cp', 'opt':True, 'use_ss':0  },
    "cp_opt_sb" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'cp', 'opt':True, 'use_ss':0  },
    
    "gecode_reg_ss" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'gecode', 'opt':False, 'use_ss':1  },
    "gecode_sb_ss" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'gecode', 'opt':False, 'use_ss':1  },
    "gecode_opt_reg_ss" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'gecode', 'opt':True, 'use_ss':1  },
    "gecode_opt_sb_ss" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'gecode', 'opt':True, 'use_ss':1  },
    "chuffed_reg_ss" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'chuffed', 'opt':False, 'use_ss':1  },
    "chuffed_sb_ss" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'chuffed', 'opt':False, 'use_ss':1  },
    "chuffed_opt_reg_ss" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'chuffed', 'opt':True, 'use_ss':1  },
    "chuffed_opt_sb_ss" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'chuffed', 'opt':True, 'use_ss':1  },
    "cp_reg_ss" :{ 'model':f'{BASE_DIR}/cp_model.mzn', 'solver':'cp', 'opt':False, 'use_ss':1  },
    "cp_sb_ss" :{ 'model':f'{BASE_DIR}/cp_model_sb.mzn', 'solver':'cp', 'opt':False, 'use_ss':1  },
    "cp_opt_reg_ss" :{ 'model':f'{BASE_DIR}/cp_optimal.mzn', 'solver':'cp', 'opt':True, 'use_ss':1  },
    "cp_opt_sb_ss" :{ 'model':f'{BASE_DIR}/cp_optimal_sb.mzn', 'solver':'cp', 'opt':True, 'use_ss':1  },
}

unsat_template = {
    'time': 300,    
    'optimal':False,
    'obj':'null',
    'sol':[],
}


# ======================
# Helper: run instance
# ======================
def run_model(model_file, solver_name, n, ss, opt=False):
    
    print(f"Running {model_file} with {solver_name}, n={n} ...")
    model = minizinc.Model(model_file)
    solver = minizinc.Solver.lookup(solver_name)
    

    inst = minizinc.Instance(solver, model)
    inst["n"] = n
    inst["use_ss"] = ss


    with contextlib.redirect_stderr(io.StringIO()):
        result = inst.solve(timeout=timedelta(seconds=300))
        # pprint.pprint(result)
        if result.solution is None:
            return None
        output_item = eval(result.solution._output_item)
        opt_val = output_item['optimal'] if opt else 'True'
        obj_val = output_item['obj'] if opt else "null"
        sol = output_item['sol'] if opt  else output_item 
    
    res = {   
            "time": (result.statistics.get("solveTime", 0)).seconds,
            "optimal":opt_val,
            "obj":obj_val,
            "sol":sol,
        }
    print(res)
    return res


if args.n==0:
    print('---------------------------start---------------------------')
    model_names = MODEL_NAMES
else:
    mod_type = int(input("Select what type of models you want to run \n 1. Decision Models \n 2. Optimization Models \n 3. All\n\noption: "))
    if mod_type == 1:
        model_names = {k: v for k, v in MODEL_NAMES.items() if not v.get("opt", False)}
    elif mod_type == 2:
        model_names = {k: v for k, v in MODEL_NAMES.items() if v.get("opt", False)}
    
for n in N_VALUE:
    all_results = {}
    for model_name, model_data in model_names.items():
        # print(model_data['model'],model_data['solver'])
        output = run_model(model_data['model'],model_data['solver'],n, model_data['use_ss'], model_data['opt'])
        if output is None:
            print(f'🥲 {model_name} did not find a solution for instance {n}')
            output = unsat_template
        output = {model_name:output}
        all_results.update(output)
        pprint.pprint(output)
        print('************************************')

    out_file = OUTPUT_DIR / f"{n}.json"
    existing_results = {}

    if out_file.exists():
        try:
            with out_file.open("r", encoding="utf-8") as f:
                if out_file.stat().st_size > 0:
                    existing_results = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {out_file} was corrupted or empty. Starting fresh.")
            existing_results = {}
    existing_results.update(all_results)
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(existing_results, f, indent=2, ensure_ascii=False)

    print(f"Wrote results to {out_file}")