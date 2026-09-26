# E2: how well does each method name the useful objects in an everyday scene?

283 scenes scored (LVIS v1 val / COCO 2017), all methods on the same scenes; rooms: bathroom 60, kitchen 60, living room 60, bedroom 60, dining 43. Scenes per method before intersecting: {'static': 283, 'clip': 283, 'blip2_orig': 283, 'blip2_caption': 283, 'blip2_qa': 283, 'qwen_vl': 283}. AAC vocabulary: 96 LVIS categories (comb, pill not in this LVIS release).

## First screen (top 3 items)

| Method | precision@3 | pooled | lenient | verifiable@3 | recall@3 | hit@3 | hit lenient | median s/scene | lists < 3 items |
|---|---|---|---|---|---|---|---|---|---|
| static | 0.297 (0.266–0.327) (n=283) | 0.297 | 0.299 | 1.000 | 0.153 (0.138–0.169) | 0.661 (0.604–0.717) | 0.668 | 0.00 | 0 |
| clip | 0.897 (0.870–0.921) (n=279) | 0.886 | 0.900 | 0.610 | 0.336 (0.311–0.362) | 0.968 (0.947–0.986) | 0.972 | 0.07 | 0 |
| blip2_orig | 0.304 (0.251–0.357) (n=283) | 0.304 | 0.304 | 0.333 | 0.000 (0.000–0.000) | 0.304 (0.251–0.357) | 0.304 | 0.13 | 0 |
| blip2_caption | 0.992 (0.983–0.998) (n=242) | 0.989 | 0.992 | 0.445 | 0.222 (0.201–0.244) | 0.855 (0.813–0.898) | 0.883 | 0.41 | 70 |
| blip2_qa | 0.949 (0.930–0.967) (n=263) | 0.943 | 0.951 | 0.595 | 0.292 (0.268–0.318) | 0.926 (0.894–0.954) | 0.943 | 0.51 | 81 |
| qwen_vl | 0.970 (0.955–0.983) (n=272) | 0.968 | 0.970 | 0.700 | 0.346 (0.320–0.371) | 0.958 (0.933–0.979) | 0.961 | 1.90 | 4 |

LVIS-only check (no COCO extension), precision@3 / verifiable@3: static 0.947 / 0.095; clip 0.997 / 0.484; blip2_orig 1.000 / 0.004; blip2_caption 1.000 / 0.316; blip2_qa 1.000 / 0.412; qwen_vl 0.996 / 0.559

## Deeper lists

| Method | precision@6 | recall@6 | recall lenient@6 | precision@12 | recall@12 | verifiable@12 |
|---|---|---|---|---|---|---|
| static | 0.269 | 0.249 (0.232–0.265) | 0.252 | 0.248 | 0.455 | 0.852 |
| clip | 0.790 | 0.468 (0.438–0.498) | 0.489 | 0.647 | 0.592 | 0.404 |
| blip2_orig | 0.304 | 0.000 (0.000–0.000) | 0.000 | 0.304 | 0.000 | 0.083 |
| blip2_caption | 0.988 | 0.240 (0.216–0.265) | 0.263 | 0.988 | 0.240 | 0.120 |
| blip2_qa | 0.947 | 0.312 (0.287–0.338) | 0.327 | 0.947 | 0.313 | 0.167 |
| qwen_vl | 0.964 | 0.492 (0.465–0.520) | 0.534 | 0.957 | 0.537 | 0.313 |

## Paired differences (same scenes; 95% bootstrap CI)

| A − B | metric | difference | n |
|---|---|---|---|
| qwen_vl − static | hit@3 | 0.297 (0.240–0.360) | 283 |
| qwen_vl − static | recall@6 | 0.244 (0.211–0.277) | 283 |
| qwen_vl − static | precision@3 | 0.676 (0.641–0.710) | 272 |
| qwen_vl − clip | hit@3 | -0.011 (-0.042–0.021) | 283 |
| qwen_vl − clip | recall@6 | 0.025 (-0.005–0.053) | 283 |
| qwen_vl − clip | precision@3 | 0.073 (0.045–0.103) | 268 |
| clip − static | hit@3 | 0.307 (0.251–0.367) | 283 |
| clip − static | recall@6 | 0.219 (0.184–0.256) | 283 |
| clip − static | precision@3 | 0.603 (0.563–0.642) | 279 |
| qwen_vl − blip2_orig | hit@3 | 0.654 (0.597–0.707) | 283 |
| qwen_vl − blip2_orig | recall@6 | 0.492 (0.466–0.520) | 283 |
| qwen_vl − blip2_orig | precision@3 | 0.654 (0.591–0.711) | 272 |
| clip − blip2_orig | hit@3 | 0.664 (0.604–0.721) | 283 |
| clip − blip2_orig | recall@6 | 0.468 (0.438–0.497) | 283 |
| clip − blip2_orig | precision@3 | 0.596 (0.533–0.659) | 279 |
| blip2_caption − static | hit@3 | 0.194 (0.124–0.265) | 283 |
| blip2_caption − static | recall@6 | -0.009 (-0.037–0.020) | 283 |
| blip2_caption − static | precision@3 | 0.709 (0.677–0.742) | 242 |
| blip2_qa − static | hit@3 | 0.265 (0.198–0.329) | 283 |
| blip2_qa − static | recall@6 | 0.063 (0.035–0.090) | 283 |
| blip2_qa − static | precision@3 | 0.660 (0.624–0.697) | 263 |
| qwen_vl − blip2_caption | hit@3 | 0.102 (0.057–0.152) | 283 |
| qwen_vl − blip2_caption | recall@6 | 0.253 (0.224–0.280) | 283 |
| qwen_vl − blip2_caption | precision@3 | -0.020 (-0.038–-0.004) | 232 |
| qwen_vl − blip2_qa | hit@3 | 0.032 (-0.007–0.074) | 283 |
| qwen_vl − blip2_qa | recall@6 | 0.181 (0.153–0.209) | 283 |
| qwen_vl − blip2_qa | precision@3 | 0.019 (-0.004–0.042) | 252 |
| clip − blip2_caption | hit@3 | 0.113 (0.067–0.163) | 283 |
| clip − blip2_caption | recall@6 | 0.228 (0.202–0.255) | 283 |
| clip − blip2_caption | precision@3 | -0.087 (-0.116–-0.060) | 238 |
| clip − blip2_qa | hit@3 | 0.042 (0.007–0.081) | 283 |
| clip − blip2_qa | recall@6 | 0.156 (0.127–0.186) | 283 |
| clip − blip2_qa | precision@3 | -0.053 (-0.082–-0.024) | 259 |

## By room

| Method | Room | n | precision@3 | recall@6 | hit@3 |
|---|---|---|---|---|---|
| blip2_caption | bathroom | 60 | 0.991 | 0.367 | 0.900 |
| blip2_caption | bedroom | 60 | 0.983 | 0.320 | 0.967 |
| blip2_caption | dining | 43 | 1.000 | 0.141 | 0.721 |
| blip2_caption | kitchen | 60 | 1.000 | 0.140 | 0.750 |
| blip2_caption | living room | 60 | 0.991 | 0.203 | 0.900 |
| blip2_orig | bathroom | 60 | 0.167 | 0.000 | 0.167 |
| blip2_orig | bedroom | 60 | 0.200 | 0.000 | 0.200 |
| blip2_orig | dining | 43 | 0.535 | 0.000 | 0.535 |
| blip2_orig | kitchen | 60 | 0.350 | 0.000 | 0.350 |
| blip2_orig | living room | 60 | 0.333 | 0.000 | 0.333 |
| blip2_qa | bathroom | 60 | 0.963 | 0.461 | 0.967 |
| blip2_qa | bedroom | 60 | 0.958 | 0.339 | 0.983 |
| blip2_qa | dining | 43 | 0.969 | 0.163 | 0.744 |
| blip2_qa | kitchen | 60 | 0.924 | 0.270 | 0.950 |
| blip2_qa | living room | 60 | 0.940 | 0.283 | 0.933 |
| clip | bathroom | 60 | 0.946 | 0.676 | 0.983 |
| clip | bedroom | 60 | 0.972 | 0.486 | 1.000 |
| clip | dining | 43 | 0.919 | 0.488 | 0.977 |
| clip | kitchen | 60 | 0.750 | 0.313 | 0.917 |
| clip | living room | 60 | 0.898 | 0.381 | 0.967 |
| qwen_vl | bathroom | 60 | 1.000 | 0.594 | 0.900 |
| qwen_vl | bedroom | 60 | 0.977 | 0.505 | 0.950 |
| qwen_vl | dining | 43 | 0.956 | 0.451 | 0.953 |
| qwen_vl | kitchen | 60 | 0.949 | 0.400 | 0.983 |
| qwen_vl | living room | 60 | 0.967 | 0.501 | 1.000 |
| static | bathroom | 60 | 0.372 | 0.248 | 0.867 |
| static | bedroom | 60 | 0.144 | 0.325 | 0.367 |
| static | dining | 43 | 0.302 | 0.143 | 0.698 |
| static | kitchen | 60 | 0.450 | 0.224 | 0.783 |
| static | living room | 60 | 0.217 | 0.273 | 0.600 |

## Item status (all ranks)

```
status         correct  unverifiable  wrong
method                                     
blip2_caption    0.481         0.511  0.007
blip2_orig       0.101         0.667  0.232
blip2_qa         0.597         0.363  0.040
clip             0.254         0.596  0.150
qwen_vl          0.537         0.434  0.030
static           0.212         0.148  0.640
```

## Most frequent items that matched no LVIS category

```
method
blip2_caption    bathroom (50), living room (40), kitchen (35),...
blip2_orig                                object (283), area (283)
blip2_qa         window (30), shower (11), people (8), food (7)...
qwen_vl          rug (22), window (22), picture (12), wall (7),...
```

## Examples (first 3 audit scenes)

```
scene 239013 (living room), AAC objects present: blanket, chair, coffee_table, cushion, fan, flower_arrangement, pillow, sofa, vase
  static     : chair[c], bottle[w], sink[w], sofa[c], bed[w], book[u]
  clip       : coffee table[c], dining table[u], sofa[c], recliner[u], cushion[c], armchair[u]
  blip2_orig : object[u], person[w], area[u]
  blip2_caption: living room[u], couches[c], table[u]
  blip2_qa   : couch[c], coffee table[c], window[u]
  qwen_vl    : couch[c], coffee table[c], vase[c], pillow[c], rug[u], chair[c]
scene 101630 (bathroom), AAC objects present: bathtub, bottle, sink, toothbrush, toothpaste, towel, vase
  static     : chair[w], bottle[c], sink[c], sofa[w], bed[w], book[u]
  clip       : sink[c], bathtub[c], soap[u], toothbrush[c], desk[u], toilet[w]
  blip2_orig : object[u], person[w], area[u]
  blip2_caption: bathroom counter[u], sink[c], mirror[u]
  blip2_qa   : sink[c], mirror[u], towel[c], bottle of shampoo[c]
  qwen_vl    : toothbrush[c], toothpaste[c], soap[u], lotion[u], hairbrush[u], towel[c]
scene 381330 (kitchen), AAC objects present: banana, bowl, microwave_oven, stove
  static     : chair[w], bottle[w], sink[w], sofa[w], bed[w], book[u]
  clip       : banana[c], apple[w], dining table[u], cookie[u], orange[w], remote control[u]
  blip2_orig : object[u], person[c], area[u]
  blip2_caption: little girl[c], banana[c], kitchen[u]
  blip2_qa   : child[c], banana[c]
  qwen_vl    : banana[c], kitchen[u], stove[c]
```

Status letters: c = correct, w = wrong (verified absent), u = unverifiable.

Audit: rate `audit_sheet.csv` (two Y/N columns). The method key is in `audit_key_private/`: do not open it, or give it to the rater, before rating is finished.
