
#%%

import pandas as pd
import cvxpy as cp
from plotly import graph_objects as go

#%%
def get_position(specific_techs,all_techs):
    return [i for i,j in enumerate(all_techs) if j in specific_techs]
#%%
# Read the data

Demand = pd.read_excel("Demand.xlsx",index_col=0)/4
Capacity = pd.read_excel("Capacity.xlsx",index_col=0)
Costs = pd.read_excel("Costs.xlsx",index_col=0)
AvailabilityMin = pd.read_excel("AvailabilityMin.xlsx",index_col=0)
AvailabilityMax = pd.read_excel("AvailabilityMax.xlsx",index_col=0)
Emission = pd.read_excel("Emission.xlsx",index_col=0)


# %%
# Sets
Technologies = Capacity.columns.tolist()
TechMax = AvailabilityMax.columns.tolist()
TechMin = AvailabilityMin.columns.tolist()
Hours = Demand.index.tolist()
# %%

def run_model():
    # Variables
    Production = cp.Variable(
        shape = (len(Hours),len(Technologies)),
        nonneg = True,
    )

# Equations
    Constraints = {}

    # Supply Balance

    Constraints["Balance"] = cp.sum(Production,axis=1,keepdims=True)==Demand.values

    # Available Capacity
    Constraints["AvailabilityMin"] = Production[:,get_position(TechMin,Technologies)] >= AvailabilityMin.values * Capacity[TechMin].values
    Constraints["AvailabilityMax"] = Production[:,get_position(TechMax,Technologies)] <= AvailabilityMax.values * Capacity[TechMax].values

    #%%
    # Objective Function
    VarCost = cp.multiply(cp.sum(Production,axis=0,) ,Costs.loc["Variable"].values)
    CarbonCost = cp.multiply(cp.sum(Production,axis=0,) ,Costs.loc["CO2Tax"].values*Emission.loc["Coefficient"].values)

    Objective = cp.Minimize(cp.sum(VarCost))

    #%%
    # Solving the problem
    Problem = cp.Problem(Objective,list(Constraints.values()))
    Problem.solve(solver="GUROBI",verbose=False)
    #%%
    Production = pd.DataFrame(
        Production.value,
        index = Hours,
        columns = Technologies,
    )
    #%%
    ShadowPrice = Constraints["Balance"].dual_value
    VariableCost = pd.DataFrame(
        Production.values * (Costs.loc["Variable"].values+Costs.loc["CO2Tax"].values*Emission.loc["Coefficient"].values),
        index = Production.index,
        columns= Production.columns,
    )
    VariableCost["Sum"] = VariableCost.sum(1)
    VariableCost["ProductionCost"] = VariableCost["Sum"]/Demand["Demand"]

    TotalCost = (VarCost+CarbonCost).value.sum()

    return Production,VariableCost,ShadowPrice,TotalCost

def plot(period,scenario):
    fig = go.Figure()

    for tech in Technologies:
        fig.add_trace(
            go.Scatter(
                x = period,
                y = Production.loc[period,tech],
                name = tech,
                stackgroup = "one",
                line_width = 0
            )
        )

    fig.add_trace(
        go.Scatter(
            x = period,
            y = Demand.loc[period,"Demand"],
            name = "Demand",
            marker_color = "black"
        )
    )

    fig.update_layout(
        {
            "yaxis":{"title":"MWh"},
            "title": f"Electricity Dispatch {scenario}"
        }
    )
    fig.show()
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x = period,
            y = VariableCost.loc[period,"ProductionCost"]*0.8
        )
    )

    fig.update_layout(
        {
            "yaxis":{"title":"Euro/MWh"},
            "title": f"Production Cost {scenario}"
        }
    )

    fig.show()
    # #%%
    # period = period
    # period[0]-=1
    # period[-1]-=1
    # fig = go.Figure()

    # fig.add_trace(
    #     go.Scatter(
    #         x = period,
    #         y = (ShadowPrice[period].ravel())*0.8
    #     )
    # )

    # fig.update_layout(
    #     {
    #         "yaxis":{"title":"Euro/MWh"},
    #         "title": "Shadow Cost"
    #     }
    # )

    # fig.show()

   
    share = Production.sum().to_frame()

    fig = go.Figure(
        data=[
            go.Pie(
                labels=share.index, values=share.values.ravel(), pull=[0 if i != "Gas Power Plants" else 0.2 for i in share.index ],
                )
            ]
        )
    fig.show()
#%%
Diff = pd.DataFrame(index = Hours,columns = ['Baseline',"Gas Price Shock"])
# Baseline
Production,VariableCost,ShadowPrice,TotalCost = run_model()
Diff.loc[Hours,"Baseline"] = VariableCost["ProductionCost"].values
average_cost_baseline = VariableCost["ProductionCost"].mean()
AverageCost_baseline = TotalCost/Demand["Demand"].sum()
#%%
plot(period = list(range(1,365)),scenario="baseline")

#%%
# 10% increase in ng price
Costs.loc["Variable","Gas Power Plants"]*=1.1

Production,VariableCost,ShadowPrice,TotalCost = run_model()
Diff.loc[Hours,"Gas Price Shock"] = VariableCost["ProductionCost"].values
average_cost_shock = VariableCost["ProductionCost"].mean()
plot(period = list(range(1,25)),scenario="baseline")
AverageCost_shock = TotalCost/Demand["Demand"].sum()

# %%
Diff.loc[list(range(1,25)),:].plot()

# %%
