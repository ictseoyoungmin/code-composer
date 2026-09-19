"""Canonical hard-constraint contract shared across authoring, IR validation, and arrangement."""

HARD_CONSTRAINT_KEYS=frozenset({'bpm','root','scale','forbidden_roles'})
FORBIDDEN_ROLE_NAMES=frozenset({'lead','topline','pad','bass','drums','arp'})


class HardConstraintError(ValueError):
    pass


def validate_hard_constraints_dict(hard_constraints):
    if not isinstance(hard_constraints,dict):
        raise HardConstraintError('hard_constraints must be an object')

    unknown=set(hard_constraints)-HARD_CONSTRAINT_KEYS
    if unknown:
        raise HardConstraintError(f'unknown hard constraint key(s): {sorted(unknown)}')

    roles=hard_constraints.get('forbidden_roles',[])
    if not isinstance(roles,list):
        raise HardConstraintError('hard_constraints.forbidden_roles must be an array')
    if any(not isinstance(role,str) for role in roles):
        raise HardConstraintError('hard_constraints.forbidden_roles entries must be strings')
    if len(set(roles)) != len(roles):
        raise HardConstraintError('hard_constraints.forbidden_roles must not contain duplicates')
    unknown_roles=set(roles)-FORBIDDEN_ROLE_NAMES
    if unknown_roles:
        raise HardConstraintError(f'unknown forbidden role(s): {sorted(unknown_roles)}')
    return hard_constraints


def forbidden_roles_from_ir(ir):
    """Return canonical forbidden roles from an IR, including old compiled-brief fallback."""
    hard_constraints=ir.get('hard_constraints')
    if not isinstance(hard_constraints,dict):
        hard_constraints=(ir.get('composer_plan',{}).get('brief',{}) or {}).get('hard_constraints',{})
    if not isinstance(hard_constraints,dict):
        return set()
    roles=hard_constraints.get('forbidden_roles',[])
    if not isinstance(roles,list):
        return set()
    return {role for role in roles if isinstance(role,str)}

def track_arrangement_role(track):
    tid=track.get('id')
    if tid in FORBIDDEN_ROLE_NAMES:
        return tid
    source=track.get('source',{})
    derived=source.get('derived_from',{}) if isinstance(source,dict) else {}
    return derived.get('role') if isinstance(derived,dict) else None


def enforce_forbidden_track_events(tracks, ir):
    """Mutate track events to satisfy forbidden roles while preserving track topology."""
    forbidden=forbidden_roles_from_ir(ir)
    if not forbidden:
        return tracks
    for track in tracks:
        role=track_arrangement_role(track)
        if role not in forbidden:
            continue
        old_events=list(track.get('events',[]))
        track['events']=[]
        track['hard_constraint']={
            'forbidden_role':role,
            'suppressed_event_count':len(old_events),
        }
        if 'arrangement_meta' in track:
            for meta in track.get('arrangement_meta',[]):
                meta['event_count']=0
                meta['hard_constraint_forbidden']=True
    return tracks


__all__=[
    'HARD_CONSTRAINT_KEYS','FORBIDDEN_ROLE_NAMES','HardConstraintError',
    'validate_hard_constraints_dict','forbidden_roles_from_ir',
    'track_arrangement_role','enforce_forbidden_track_events',
]
