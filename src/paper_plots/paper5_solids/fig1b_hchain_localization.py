#%%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from deeperwin.run_tools.geometry_database import load_geometries, load_datasets, Geometry
from deeperwin.utils.plotting import get_discrete_colors_from_cmap
from typing import Iterable

all_geoms = load_geometries()
def get_data_from_geometry(row):
    geom = all_geoms[row.geom]
    row["n_atoms"] = geom.n_atoms * geom.periodic.supercell[0]
    row["R"] = geom.R[1][0] - geom.R[0][0]
    row["k"] = geom.periodic.k_twist[0]
    return row

# Data from DPE runs
csv_fnames = [
    ("/home/mscherbela/runs/paper5_solids/HChains/evaluations/DZ_Mixed_v4.csv", "ours_pretrain"),
    ("/home/mscherbela/runs/paper5_solids/HChains/evaluations/Reuse40.csv", "ours_reuse"),
]
dpe_data: Iterable[pd.DataFrame] = []
for fname, method in csv_fnames:
    df = pd.read_csv(fname)
    if "n_pretrain" not in df:
        df["n_pretrain"] = None
    columns = dict(loc_abs_0="z", loc_abs_0_sigma_corr="z_sigma", geom="geom", weight="weight", epoch="epochs", n_pretrain="n_pretrain")
    df = df[list(columns.keys())].rename(columns=columns)
    df["method"] = method
    if "reuse" in method:
        df["method"] += df.n_pretrain.apply(lambda x: f"_{x/1000:.0f}kpre")
    df["method"] += df.epochs.apply(lambda x: f"_{x/1000:.0f}k")
    dpe_data.append(df)
dpe_data = pd.concat(dpe_data)
dpe_data = dpe_data.apply(get_data_from_geometry, axis=1)
# dpe_data = dpe_data[dpe_data.k > 0]
dpe_data["weight_sqr"] = dpe_data.weight ** 2
dpe_data["z_weighted"] = dpe_data.z * dpe_data.weight
dpe_data["z_sigma_sqr_weighted"] = dpe_data.z_sigma ** 2 * dpe_data.weight_sqr

# Pivot the data to get twist-average results
groupings = ["method", "epochs", "n_atoms", "R"]
pivot = dpe_data.groupby(groupings).agg(
    z_weighted=("z_weighted", "sum"),
    weight=("weight", "sum"),
    weight_sqr=("weight_sqr", "sum"),
    z_sigma_sqr_weighted=("z_sigma_sqr_weighted", "sum"),
    ).reset_index()
pivot["z"] = pivot.z_weighted / pivot.weight
pivot["z_sigma"] = np.sqrt(pivot.z_sigma_sqr_weighted / pivot.weight_sqr)

# Data from other works
df_ref = pd.read_csv("/home/mscherbela/runs/references/Motta_et_al_metal_insulator_transition.csv", sep=';')
df_ref["method"] = df_ref.source + ", " + df_ref.method
df = pd.concat([pivot, df_ref])
df = df.sort_values(["method", "n_atoms", "R"])

colors_red = get_discrete_colors_from_cmap(4, "Reds", 0.3, 1.0)
colors_blue = get_discrete_colors_from_cmap(3, "Blues", 0.6, 1.0)
colors_orange = get_discrete_colors_from_cmap(3, "Oranges", 0.4, 1.0)


curves_to_plot = [
    ("Motta (2020), AFQMC", 40, "--", 'o', "black", "AFQMC, $N_\\mathrm{atoms}$=40"),
    ("Motta (2020), DMC", 40, "dashdot", 'o', "slategray", "DMC, $N_\\mathrm{atoms}$=40"),
    ("ours_pretrain_200k", 12, "-", "none", colors_blue[0], None),
    ("ours_pretrain_200k", 16, "-", "none", colors_blue[1], "Ours pre-train, $N_\\mathrm{atoms}$=12-20"),
    ("ours_pretrain_200k", 20, "-", "none", colors_blue[2], None),
    ("ours_reuse_200kpre_5k", 40, "-", "none", "red", "Ours fine-tune, $N_\\mathrm{atoms}$=40"),
]

text_labels = [
    (3.1, 0.56, "$N_\\mathrm{atoms}$=12"),
    (3.1, 0.66, "$N_\\mathrm{atoms}$=16"),
    (3.1, 0.75, "$N_\\mathrm{atoms}$=20"),
    (3.1, 0.84, "$N_\\mathrm{atoms}$=40"),
]

plt.close("all")
fig, ax = plt.subplots(1, 1, figsize=(5, 4))
for (method, n_atoms, ls, marker, color, label) in curves_to_plot:
    df_plot = df[(df.method == method) & (df.n_atoms == n_atoms)]
    if len(df_plot) == 0:
        continue
    if any(~np.isnan(df_plot.z_sigma)) > 0:
        yerr = 2 * df_plot.z_sigma
    else:
        yerr = None
    ax.errorbar(df_plot.R,
                df_plot.z,
                yerr=yerr,
                label=label,
                color=color,
                ls=ls,
                marker=marker,
                ms=4,
                capsize=3, 
                capthick=1)

for (x, y, text), color in zip(text_labels, colors_blue + ["red"]):
    text_box = ax.text(x, y, text, fontsize=8, ha="left", va="center", color=color)
    text_box.set_bbox(dict(facecolor='white', alpha=0.8, edgecolor='none'))
ax.legend()
for z in [0,1]:
    ax.axhline(z, color="gray", lw=1)
ax.set_xlabel("$R$ / $a_0$")
ax.set_ylabel("polarization $|z|$")
ax.text(0, 1.0, "b", transform=ax.transAxes, ha="left", va="bottom", fontsize=16, fontweight="bold")


fname = "/home/mscherbela/ucloud/results/05_paper_solids/figures/HChains_MIT.pdf"
fig.savefig(fname, bbox_inches="tight")
fig.savefig(fname.replace(".pdf", ".png"), bbox_inches="tight", dpi=300)

#%%
import seaborn as sns
plt.close("all")
fig_k, ax_k = plt.subplots(1, 1, figsize=(10, 8))
# df_k = dpe_data[(dpe_data.n_atoms == 20) & (dpe_data.method.str.contains("ours_pretrain"))]
df_k = dpe_data[(dpe_data.n_atoms == 40) & (dpe_data.method.str.contains("ours_reuse"))]
sns.lineplot(df_k, x="k", y="z", hue="R", ax=ax_k, palette="tab10", markers=True, style="method")



