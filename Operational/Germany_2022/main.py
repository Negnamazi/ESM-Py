
#%%

import pandas as pd
import cvxpy as cp
from plotly import graph_objects as go

#%%
def get_position(specific_techs,all_techs):
    return [i for i,j in enumerate(all_techs) if i in specific_techs]
#%%
# Read the data

Demand = pd.read_excel("Demand.xlsx",index_col=0)
Capacity = pd.read_excel("Capacity.xlsx",index_col=0)
Costs = pd.read_excel("Costs.xlsx",index_col=0)
AvailabilityMin = pd.read_excel("AvailabilityMin.xlsx",index_col=0)
AvailabilityMax = pd.read_excel("AvailabilityMax.xlsx",index_col=0)
AvailabilityEq = pd.read_excel("AvailabilityEq.xlsx",index_col=0)


# %%
# Sets
Technologies = Capacity.columns.tolist()
TechMax = AvailabilityMax.columns.tolist()
TechMin = AvailabilityMin.columns.tolist()
TechEq = AvailabilityEq.columns.tolist()
Hours = Demand.index.tolist()
# %%
# Variables
Production = cp.Variable(
    shape = (len(Hours),len(Technologies)),
    nonneg = True,
)

#%%
# Equations
Constraints = {}

# Supply Balance

Constraints["Balance"] = cp.sum(Production,axis=1,keepdims=True)>=Demand.values

# Available Capacity
Constraints["AvailabilityMin"] = Production[:,get_position(TechMin,Technologies)] >= AvailabilityMin.values * Capacity[TechMin].values
Constraints["AvailabilityMax"] = Production[:,get_position(TechMax,Technologies)] <= AvailabilityMax.values * Capacity[TechMax].values
Constraints["AvailabilityEq"]  = Production[:,get_position(TechEq ,Technologies)] <= AvailabilityEq.values  * Capacity[TechEq].values

#%%
# Objective Function
VarCost = cp.multiply(cp.sum(Production,axis=0,) ,Costs.loc["Variable"].values)

Objective = cp.Minimize(cp.sum(VarCost))

#%%
# Solving the problem
Problem = cp.Problem(Objective,list(Constraints.values()))
Problem.solve(solver="GUROBI",verbose=True)
#%%
Production = pd.DataFrame(
    Production.value,
    index = Hours,
    columns = Technologies,
)
#%%
ShadowPrice = Constraints["Balance"].dual_value
VariableCost = pd.DataFrame(
    Production.values * Costs.loc["Variable"].values,
    index = Production.index,
    columns= Production.columns,
)
VariableCost["Sum"] = VariableCost.sum(1)
VariableCost["ProductionCost"] = VariableCost["Sum"]/Demand["Demand"]
# %%
# Some Plots
fig = go.Figure()

for tech in Technologies:
    fig.add_trace(
        go.Scatter(
            x = Hours,
            y = Production[tech],
            name = tech,
            stackgroup = "one",
            line_width = 0
        )
    )

fig.add_trace(
    go.Scatter(
        x = Hours,
        y = Demand["Demand"],
        name = "Demand",
        marker_color = "black"
    )
)

fig.update_layout(
    {
        "yaxis":{"title":"MWh"},
        "title": "Electricity Dispatch"
    }
)
fig.show()
# %%
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x = Hours,
        y = VariableCost["ProductionCost"] 
    )
)

fig.update_layout(
    {
        "yaxis":{"title":"Euro/MWh"},
        "title": "Production Cost"
    }
)

fig.show()


# %%
