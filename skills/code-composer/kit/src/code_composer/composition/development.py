def section_development(ir, section_id, profile):
    cfg=ir.get("arrangement_development",{})
    if not cfg.get("enabled",False):
        p=dict(profile)
        p["development_stage"]="legacy"
        return p,{"stage":"legacy"}

    merged=dict(cfg.get("default",{}))
    merged.update(cfg.get("sections",{}).get(section_id,{}))
    p=dict(profile)

    multipliers={
        "lead_density":"lead_density_scale",
        "topline_density":"topline_density_scale",
        "lead_fragment":"lead_fragment_scale",
        "pad_gain":"pad_gain_scale",
        "energy":"energy_scale",
    }
    for field,key in multipliers.items():
        if field in p:
            p[field]=float(p[field])*float(merged.get(key,1.0))

    p["register_shift"]=int(p.get("register_shift",0))+int(merged.get("register_shift_add",0))
    p["lead_octave"]=int(p.get("lead_octave",4))+int(merged.get("lead_octave_add",0))

    for field in ("bass","arp"):
        override=merged.get(f"{field}_active")
        if override is not None:
            p[field]=bool(override)

    stage=str(merged.get("stage","develop"))
    p["development_stage"]=stage
    return p,{
        "stage":stage,
        "rhythm_density_scale":float(merged.get("rhythm_density_scale",1.0)),
        "fill_scale":float(merged.get("fill_scale",1.0)),
        "kick_scale":float(merged.get("kick_scale",1.0)),
        "snare_scale":float(merged.get("snare_scale",1.0)),
        "hat_scale":float(merged.get("hat_scale",1.0)),
    }

def develop_rhythm_profile(ir, section_id, profile):
    cfg=ir.get("arrangement_development",{})
    if not cfg.get("enabled",False):
        return profile
    merged=dict(cfg.get("default",{}))
    merged.update(cfg.get("sections",{}).get(section_id,{}))
    p=dict(profile)
    p["density"]=max(0.0,min(1.0,float(p.get("density",1.0))*float(merged.get("rhythm_density_scale",1.0))))
    p["fill"]=max(0.0,min(1.0,float(p.get("fill",0.0))*float(merged.get("fill_scale",1.0))))
    for role,key in (("kick","kick_scale"),("snare","snare_scale"),("hat","hat_scale")):
        p[role]=max(0.0,float(p.get(role,1.0))*float(merged.get(key,1.0)))
    p["development_stage"]=str(merged.get("stage","develop"))
    return p

__all__=["section_development","develop_rhythm_profile"]
