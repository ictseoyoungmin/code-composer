VALID_FOREGROUND_MODES={"legacy","none","lead","topline","both","sparse"}

def section_orchestration(ir, section_id, profile):
    cfg=ir.get("orchestration_grammar",{})
    if not cfg.get("enabled",False):
        return {
            "mode":"legacy",
            "lead_active":True,
            "topline_active":bool(profile.get("topline_active",False)),
            "lead_density_scale":1.0,
            "topline_density_scale":1.0,
            "sparse_role":"lead",
        }

    merged=dict(cfg.get("default",{}))
    merged.update(cfg.get("sections",{}).get(section_id,{}))
    mode=merged.get("foreground_mode","none")
    if mode not in VALID_FOREGROUND_MODES:
        raise ValueError(f"unknown foreground_mode: {mode}")

    sparse_role=merged.get("sparse_role","lead")
    if sparse_role not in {"lead","topline"}:
        raise ValueError("sparse_role must be lead or topline")

    if mode=="none":
        lead_active=topline_active=False
    elif mode=="lead":
        lead_active,topline_active=True,False
    elif mode=="topline":
        lead_active,topline_active=False,True
    elif mode=="both":
        lead_active=topline_active=True
    elif mode=="sparse":
        lead_active=(sparse_role=="lead")
        topline_active=(sparse_role=="topline")
    else:
        lead_active=True
        topline_active=bool(profile.get("topline_active",False))

    sparse_scale=float(merged.get("sparse_density_scale",0.30))
    lead_scale=float(merged.get("lead_density_scale",1.0))
    topline_scale=float(merged.get("topline_density_scale",1.0))
    if mode=="sparse":
        if lead_active:
            lead_scale*=sparse_scale
        if topline_active:
            topline_scale*=sparse_scale

    return {
        "mode":mode,
        "lead_active":lead_active,
        "topline_active":topline_active,
        "lead_density_scale":lead_scale,
        "topline_density_scale":topline_scale,
        "sparse_role":sparse_role,
    }

def effective_section_profile(ir, section_id, profile):
    p=dict(profile)
    plan=section_orchestration(ir,section_id,p)
    p["orchestration_mode"]=plan["mode"]
    p["lead_active"]=plan["lead_active"]
    p["topline_active"]=plan["topline_active"]
    p["lead_density"]=float(p.get("lead_density",0.0))*plan["lead_density_scale"]
    p["topline_density"]=float(p.get("topline_density",0.0))*plan["topline_density_scale"]
    return p,plan

__all__=["section_orchestration","effective_section_profile","VALID_FOREGROUND_MODES"]
