# Identifiability study: identifiability_volume_fractions

Parameters: ['Negative electrode active material volume fraction', 'Positive electrode active material volume fraction']
Truth: {'Negative electrode active material volume fraction': 0.75, 'Positive electrode active material volume fraction': 0.665}
Evaluation point: [0.7411567214376811, 0.6693925564174432]

## hessian_single
- message: The optimiser has located a minimum. There may be a correlation between these parameters.

## hessian_multi
- message: The optimiser has located a minimum.

## fim_single
- condition_number: 21.59544722658189
- correlation: [[1.0000000000000002, -0.75582982829257], [-0.7558298282925704, 0.9999999999999999]]

## fim_multi
- condition_number: 35.53234538088108
- correlation: [[1.0, -0.8152156054529373], [-0.815215605452937, 1.0000000000000002]]

## profiles

## bootstrap
- per_parameter: {'Negative electrode active material volume fraction': {'mean': 0.748914640859603, 'std': 0.0054976186534733676, 'min': 0.7352167987859081, 'max': 0.7566451599318932, 'truth': 0.75}, 'Positive electrode active material volume fraction': {'mean': 0.6652063301741118, 'std': 0.0023331850419658837, 'min': 0.6619327265696271, 'max': 0.6711219340909141, 'truth': 0.665}}

## sobol_single
- S1_mean: [0.34335337578146874, 0.6464173095649003]
- ST_mean: [0.3470345341489443, 0.6473904574995021]

## sobol_multi
- S1_mean: [0.3143258456891749, 0.6758965029881588]
- ST_mean: [0.3176853893106432, 0.6767636629449969]

## mcmc
- posterior_mean: [0.7374415906290327, 0.6708450547596407, 0.0027207341803209845]
- posterior_std: [0.011346048427942398, 0.0037743033901095637, 0.00026098803136347153]
- posterior_corrcoef: [[1.0, -0.850493548779479, 0.5961623218041694], [-0.8504935487794791, 0.9999999999999999, -0.6243069796319344], [0.5961623218041694, -0.6243069796319344, 0.9999999999999998]]
- ci95: [[0.718079403907538, 0.7545289068568846], [0.6636625078769508, 0.6769577985694507], [0.0018534724135571765, 0.0029023634485387233]]

