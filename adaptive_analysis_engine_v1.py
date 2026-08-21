
from __future__ import annotations
from typing import Any
import pandas as pd

def _num(s): return pd.to_numeric(s, errors="coerce")
def _pct(cur, prev):
    return None if prev in (0, None) else (cur-prev)/abs(prev)*100

def analyze_core_performance(data):
    out = {"module":"sales_performance","title":"Sales Performance","available":False,
           "metrics":{},"monthly":[],"insights":[]}
    if "revenue" not in data.columns: return out
    revenue = _num(data["revenue"]).sum()
    orders = int(data["order_id"].nunique()) if "order_id" in data.columns else len(data)
    quantity = _num(data["quantity"]).sum() if "quantity" in data.columns else None
    out["available"] = True
    out["metrics"] = {
        "revenue": float(revenue),"orders":orders,
        "quantity": float(quantity) if quantity is not None else None,
        "aov": float(revenue/orders) if orders else None,
    }
    if "date" in data.columns:
        w=data.copy()
        w["_month"]=pd.to_datetime(w["date"],errors="coerce").dt.to_period("M").astype(str)
        agg={"revenue":("revenue","sum")}
        agg["orders"]=("order_id","nunique") if "order_id" in w.columns else ("revenue","size")
        m=w.dropna(subset=["_month"]).groupby("_month").agg(**agg).reset_index()
        if "quantity" in w.columns:
            q=w.groupby("_month")["quantity"].sum().reset_index(name="quantity")
            m=m.merge(q,on="_month",how="left")
        for row in m.to_dict("records"):
            row["aov"]=row["revenue"]/row["orders"] if row["orders"] else None
            out["monthly"].append(row)
        if len(out["monthly"])>=2:
            p,c=out["monthly"][-2],out["monthly"][-1]
            rp=_pct(c["revenue"],p["revenue"]); op=_pct(c["orders"],p["orders"]); ap=_pct(c["aov"],p["aov"])
            if rp is not None and op is not None and ap is not None:
                driver="order volume" if abs(op)>abs(ap) else "average order value"
                out["insights"].append({"type":"period_change","message":f"Revenue changed {rp:+.1f}% from {p['_month']} to {c['_month']}.","driver":driver,"revenue_change_pct":rp,"orders_change_pct":op,"aov_change_pct":ap})
    return out

def analyze_products(data):
    ok="product" in data.columns and "revenue" in data.columns
    out={"module":"products","title":"Products","available":ok,"top_products":[],"concentration":None,"insights":[]}
    if not ok:return out
    r=data.groupby("product")["revenue"].sum().sort_values(ascending=False)
    out["top_products"]=r.head(10).reset_index(name="revenue").to_dict("records")
    if len(r) and r.sum(): out["concentration"]={"top_product":str(r.index[0]),"top_product_revenue_share_pct":float(r.iloc[0]/r.sum()*100)}
    return out

def analyze_customers(data):
    ok="customer" in data.columns and "revenue" in data.columns
    out={"module":"customers","title":"Customers","available":ok,"top_customers":[],"concentration":None,"insights":[]}
    if not ok:return out
    r=data.groupby("customer")["revenue"].sum().sort_values(ascending=False)
    out["top_customers"]=r.head(10).reset_index(name="revenue").to_dict("records")
    if len(r) and r.sum(): out["concentration"]={"top_customer":str(r.index[0]),"top_customer_revenue_share_pct":float(r.iloc[0]/r.sum()*100)}
    return out

def analyze_dimension(data, dimension, title):
    ok=dimension in data.columns and "revenue" in data.columns
    out={"module":dimension,"title":title,"available":ok,"ranked_values":[],"insights":[]}
    if ok:
        g=data.groupby(dimension)["revenue"].sum().sort_values(ascending=False)
        out["ranked_values"]=g.head(10).reset_index(name="revenue").to_dict("records")
    return out

def analyze_discounts(data):
    ok="discount_pct" in data.columns or "discount_amount" in data.columns
    out={"module":"discounts","title":"Discounts","available":ok,"metrics":{},"insights":[]}
    if not ok:return out
    if "discount_pct" in data.columns:
        d=_num(data["discount_pct"]); out["metrics"]["average_discount_pct"]=float(d.mean()) if d.notna().any() else None
    if "discount_amount" in data.columns:
        out["metrics"]["discount_amount"]=float(_num(data["discount_amount"]).sum())
    return out

def _return_flag(s):
    return s.astype(str).str.strip().str.lower().isin({"returned","return","yes","y","true","refunded","refund"})

def analyze_returns(data):
    ok="return_status" in data.columns or "return_amount" in data.columns
    out={"module":"returns","title":"Returns","available":ok,"metrics":{},"insights":[]}
    if not ok:return out

    returned = None
    if "return_status" in data.columns:
        returned = _return_flag(data["return_status"])
        out["metrics"]["return_rate_pct"] = float(
            returned.mean() * 100
        )

        if "order_id" in data.columns:
            total_orders = data["order_id"].nunique()
            returned_orders = data.loc[
                returned,
                "order_id",
            ].nunique()
            if total_orders:
                out["metrics"]["returned_order_rate_pct"] = float(
                    returned_orders / total_orders * 100
                )

    if "return_amount" in data.columns:
        out["metrics"]["return_amount"] = float(
            _num(data["return_amount"]).sum()
        )
    elif returned is not None and "revenue" in data.columns:
        # When an explicit return amount is absent, use revenue on rows
        # marked returned as a transparent proxy for returned value.
        out["metrics"]["return_amount"] = float(
            _num(data.loc[returned, "revenue"]).sum()
        )
        out["metrics"]["return_amount_is_estimated"] = True

    return out

def analyze_costs(data):
    ok="cost" in data.columns and "revenue" in data.columns
    out={"module":"profitability","title":"Costs & Margin","available":ok,"metrics":{},"insights":[]}
    if not ok:return out
    rev=_num(data["revenue"]); cost=_num(data["cost"]); margin=rev-cost
    out["metrics"]={"revenue":float(rev.sum()),"cost":float(cost.sum()),"gross_margin":float(margin.sum()),"gross_margin_pct":float(margin.sum()/rev.sum()*100) if rev.sum() else None}
    return out

def analyze_modules(data, semantic_model, data_quality=None):
    c=semantic_model.get("capabilities",{}); modules={}
    if c.get("sales_performance"): modules["sales_performance"]=analyze_core_performance(data)
    if c.get("product_analysis"): modules["products"]=analyze_products(data)
    if c.get("customer_analysis"): modules["customers"]=analyze_customers(data)
    if c.get("regional_analysis"): modules["region"]=analyze_dimension(data,"region","Regions")
    if c.get("sales_team_analysis"): modules["salesperson"]=analyze_dimension(data,"salesperson","Sales Team")
    if c.get("channel_analysis"): modules["channel"]=analyze_dimension(data,"channel","Channels")
    if c.get("payment_analysis"): modules["payment_method"]=analyze_dimension(data,"payment_method","Payment Methods")
    if c.get("order_status_analysis"): modules["order_status"]=analyze_dimension(data,"order_status","Order Status")
    if c.get("discount_analysis"): modules["discounts"]=analyze_discounts(data)
    if c.get("return_analysis"): modules["returns"]=analyze_returns(data)
    if c.get("profitability_analysis"): modules["profitability"]=analyze_costs(data)
    modules["data_quality"]={"module":"data_quality","title":"Data Quality","available":data_quality is not None,"result":data_quality}
    enabled=[k for k,v in modules.items() if v.get("available")]
    return {"modules":modules,"enabled_modules":enabled,"module_count":len(enabled)}
