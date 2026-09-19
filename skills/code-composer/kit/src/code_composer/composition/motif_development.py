from __future__ import annotations

from copy import deepcopy

from ..core.theory import NOTE_TO_PC, SCALES


class MotifDevelopmentError(ValueError):
    pass


def _contour(values):
    return [1 if b>a else -1 if b<a else 0 for a,b in zip(values,values[1:])]


def motif_identity_metrics(source_intervals, source_rhythm, candidate_intervals, candidate_rhythm):
    """Deterministic structural identity evidence.

    This is not a creative judgment. The Composer Agent supplies the acceptable
    `identity_floor`; the engine measures pitch/rhythm landmark retention against it.
    The floor is a QA target, not a hard compile barrier. `identity_hard_min`, when
    explicitly authored, is the only hard identity validity threshold.
    """
    if not source_intervals or not candidate_intervals:
        return {
            'score':0.0,'interval_shape':0.0,'contour':0.0,'rhythm_landmarks':0.0,'anchors':0.0,
        }
    n=min(len(source_intervals),len(candidate_intervals))
    src=list(source_intervals[:n]); cand=list(candidate_intervals[:n])
    src_norm=[x-src[0] for x in src]
    cand_norm=[x-cand[0] for x in cand]
    interval_shape=sum(1 for a,b in zip(src_norm,cand_norm) if a==b)/max(1,n)

    ca=_contour(src); cb=_contour(cand)
    contour=sum(1 for a,b in zip(ca,cb) if a==b)/max(1,min(len(ca),len(cb))) if ca and cb else 1.0

    rn=min(len(source_rhythm),len(candidate_rhythm))
    if rn:
        sa=list(source_rhythm[:rn]); ra=list(candidate_rhythm[:rn])
        ssum=sum(sa) or 1.0; rsum=sum(ra) or 1.0
        srel=[x/ssum for x in sa]; rrel=[x/rsum for x in ra]
        rhythm_landmarks=sum(1 for a,b in zip(srel,rrel) if abs(a-b)<=0.06)/rn
    else:
        rhythm_landmarks=0.0

    # First, apex and final pitch landmarks are especially recognizable.
    def apex_index(xs):
        return max(range(len(xs)), key=lambda i:(xs[i],-i))
    anchors=0.0
    checks=0
    for si,ci in ((0,0),(len(source_intervals)-1,len(candidate_intervals)-1)):
        checks+=1
        anchors += 1.0 if source_intervals[si]-source_intervals[0] == candidate_intervals[ci]-candidate_intervals[0] else 0.0
    checks+=1
    s_ai=apex_index(source_intervals); c_ai=apex_index(candidate_intervals)
    anchors += 1.0 if abs((s_ai/max(1,len(source_intervals)-1))-(c_ai/max(1,len(candidate_intervals)-1)))<=0.2 else 0.0
    anchors/=checks

    length_ratio=min(len(source_intervals),len(candidate_intervals))/max(len(source_intervals),len(candidate_intervals))
    score=(0.38*interval_shape + 0.27*contour + 0.20*rhythm_landmarks + 0.15*anchors) * (0.72+0.28*length_ratio)
    return {
        'score':round(float(score),6),
        'interval_shape':round(float(interval_shape),6),
        'contour':round(float(contour),6),
        'rhythm_landmarks':round(float(rhythm_landmarks),6),
        'anchors':round(float(anchors),6),
        'length_ratio':round(float(length_ratio),6),
    }


def _require_same_length(intervals,rhythm,name):
    if len(intervals)!=len(rhythm):
        raise MotifDevelopmentError(f'{name}: intervals/rhythm length mismatch')
    if not intervals:
        raise MotifDevelopmentError(f'{name}: motif statement cannot be empty')
    if any(float(x)<=0 for x in rhythm):
        raise MotifDevelopmentError(f'{name}: rhythm values must be > 0')


def apply_transform_chain(source_motif: dict, statement: dict) -> dict:
    intervals=list(source_motif['intervals'])
    rhythm=[float(x) for x in source_motif['rhythm']]
    _require_same_length(intervals,rhythm,'source motif')
    semitone_shift=0
    trace=[]
    relation=None

    for index,op in enumerate(statement['transform_chain']):
        kind=op['op']
        before={'intervals':list(intervals),'rhythm':list(rhythm),'semitone_shift':semitone_shift}
        if kind=='exact':
            pass
        elif kind=='call':
            intervals=list(op['intervals'])
            rhythm=[float(x) for x in op['rhythm']]
            relation={'role':'call'}
        elif kind=='fragment':
            start=int(op['start']); length=int(op['length'])
            intervals=intervals[start:start+length]
            rhythm=rhythm[start:start+length]
            if not intervals:
                raise MotifDevelopmentError(f"statement {statement['statement_id']}: fragment selects no notes")
        elif kind=='sequence':
            shift=int(op['scale_degrees'])
            intervals=[x+shift for x in intervals]
        elif kind in {'transpose','register_shift'}:
            semitone_shift += int(op['semitones'])
        elif kind=='rhythm_scale':
            factor=float(op['factor'])
            rhythm=[x*factor for x in rhythm]
        elif kind=='rhythm_rewrite':
            new=[float(x) for x in op['rhythm']]
            if len(new)!=len(intervals):
                raise MotifDevelopmentError(
                    f"statement {statement['statement_id']}: rhythm_rewrite length must equal current note count"
                )
            rhythm=new
        elif kind=='inversion':
            axis=intervals[0]
            intervals=[axis-(x-axis) for x in intervals]
        elif kind=='retrograde':
            intervals=list(reversed(intervals)); rhythm=list(reversed(rhythm))
        elif kind=='cadence_rewrite':
            tail=list(op['intervals'])
            if len(tail)>len(intervals):
                raise MotifDevelopmentError(
                    f"statement {statement['statement_id']}: cadence rewrite longer than current statement"
                )
            intervals=intervals[:-len(tail)] + tail if tail else intervals
            if 'rhythm' in op:
                tr=[float(x) for x in op['rhythm']]
                if len(tr)!=len(tail):
                    raise MotifDevelopmentError(
                        f"statement {statement['statement_id']}: cadence rhythm length must match cadence intervals"
                    )
                rhythm=rhythm[:-len(tr)] + tr if tr else rhythm
        elif kind=='ornament':
            insert_after=int(op['start'])
            extra=list(op['intervals']); extra_r=[float(x) for x in op['rhythm']]
            if len(extra)!=len(extra_r):
                raise MotifDevelopmentError(
                    f"statement {statement['statement_id']}: ornament intervals/rhythm length mismatch"
                )
            pos=min(len(intervals),insert_after+1)
            intervals=intervals[:pos]+extra+intervals[pos:]
            rhythm=rhythm[:pos]+extra_r+rhythm[pos:]
        elif kind=='response':
            intervals=list(op['intervals'])
            rhythm=[float(x) for x in op['rhythm']]
            relation={'role':'response','responds_to':op['responds_to']}
        else:
            raise MotifDevelopmentError(f'unsupported motif transform: {kind}')
        _require_same_length(intervals,rhythm,f"statement {statement['statement_id']} after {kind}")
        trace.append({'index':index,'op':deepcopy(op),'before':before,
                      'after':{'intervals':list(intervals),'rhythm':list(rhythm),'semitone_shift':semitone_shift}})

    metrics=motif_identity_metrics(
        source_motif['intervals'],source_motif['rhythm'],intervals,rhythm
    )
    floor=float(statement['identity_floor'])
    hard_min=(float(statement['identity_hard_min'])
              if statement.get('identity_hard_min') is not None else None)
    if hard_min is not None and metrics['score'] + 1e-12 < hard_min:
        raise MotifDevelopmentError(
            f"statement {statement['statement_id']} identity {metrics['score']:.4f} below hard minimum {hard_min:.4f}"
        )
    return {
        'statement_id':statement['statement_id'],
        'source_motif_id':statement['source_motif_id'],
        'intervals':intervals,
        'rhythm':rhythm,
        'semitone_shift':semitone_shift,
        'identity':metrics,
        'identity_floor':floor,
        'identity_hard_min':hard_min,
        'identity_target_met':bool(metrics['score'] + 1e-12 >= floor),
        'relation':deepcopy(relation),
        'transform_trace':trace,
        'cadence_rule':statement.get('cadence_rule'),
    }


def _scale_lattice(root,scale,lo=0,hi=127):
    pcs={(NOTE_TO_PC[root]+x)%12 for x in SCALES[scale]}
    return [m for m in range(lo,hi+1) if m%12 in pcs]


def _move_scale_steps(anchor_midi,steps,root,scale):
    lattice=_scale_lattice(root,scale)
    anchor=min(lattice,key=lambda m:(abs(m-int(anchor_midi)),m))
    idx=lattice.index(anchor)
    idx=max(0,min(len(lattice)-1,idx+int(steps)))
    return lattice[idx]


def _anchor_event(events,start,end):
    inside=[e for e in events if start-1e-9 <= float(e.get('start_beat',-1)) < end-1e-9 and 'midi' in e]
    if not inside:
        return None
    return min(inside,key=lambda e:(float(e['start_beat']),int(e['midi'])))



def validate_motif_development_contract(ir: dict, performance_ir) -> None:
    """Preflight transform execution against concrete motif materials."""
    perf=(performance_ir if isinstance(performance_ir,dict) else {
        'motif_statements':list(performance_ir.motif_statements),
        'phrases':list(performance_ir.phrases),
    })
    materials=ir.get('materials',{}).get('motifs',{})
    compiled={}
    for statement in perf.get('motif_statements',[]):
        source_id=statement['source_motif_id']
        if source_id not in materials:
            raise MotifDevelopmentError(
                f"statement {statement['statement_id']}: unknown source motif {source_id}"
            )
        compiled[statement['statement_id']]=apply_transform_chain(materials[source_id],statement)
    for phrase in perf.get('phrases',[]):
        sid=phrase.get('source_material')
        if sid not in compiled:
            continue
        total=sum(compiled[sid]['rhythm'])
        duration=float(phrase['duration_beats'])
        if total > duration + 1e-9:
            raise MotifDevelopmentError(
                f"phrase {phrase['phrase_id']}: statement duration {total:.4f} exceeds phrase duration {duration:.4f}"
            )

def realize_motif_statements(ir: dict) -> dict:
    """Compile statement-referenced phrases into concrete note events.

    Only phrases whose `source_material` is a motif statement are rewritten. Direct
    source-motif phrases keep the E1 behavior unchanged.
    """
    if 'performance_ir' not in ir:
        return deepcopy(ir)
    if ir.get('motif_development_resolved'):
        return deepcopy(ir)

    out=deepcopy(ir)
    perf=out['performance_ir']
    statements={s['statement_id']:s for s in perf.get('motif_statements',[])}
    if not statements:
        out['motif_development_resolved']=True
        out['motif_development_report']={'statement_count':0,'realized_phrase_count':0,'statements':[]}
        return out

    materials=out.get('materials',{}).get('motifs',{})
    compiled={}
    for sid,stmt in statements.items():
        source_id=stmt['source_motif_id']
        if source_id not in materials:
            raise MotifDevelopmentError(f'statement {sid}: unknown source motif {source_id}')
        compiled[sid]=apply_transform_chain(materials[source_id],stmt)

    tonal=out['tonal']; root=tonal['root']; scale=tonal['scale']
    tracks={t.get('id'):t for t in out.get('tracks',[])}
    phrase_reports=[]

    for phrase in sorted(perf.get('phrases',[]),key=lambda p:(float(p['start_beat']),p['phrase_id'])):
        sid=phrase.get('source_material')
        if sid not in compiled:
            continue
        role=phrase['role']
        if role not in tracks:
            raise MotifDevelopmentError(f"phrase {phrase['phrase_id']}: no track for role {role}")
        track=tracks[role]
        start=float(phrase['start_beat']); end=start+float(phrase['duration_beats'])
        anchor=_anchor_event(track.get('events',[]),start,end)
        if anchor is None:
            raise MotifDevelopmentError(
                f"phrase {phrase['phrase_id']}: statement realization needs an existing anchor event"
            )
        statement=compiled[sid]
        total=sum(statement['rhythm'])
        if total > float(phrase['duration_beats']) + 1e-9:
            raise MotifDevelopmentError(
                f"phrase {phrase['phrase_id']}: statement duration {total:.4f} exceeds phrase duration {float(phrase['duration_beats']):.4f}"
            )

        source=materials[statement['source_motif_id']]
        source_first=int(source['intervals'][0])
        base_anchor=int(anchor['midi'])
        # Preserve non-pitch event fields from the anchor as a role-level template.
        template={k:deepcopy(v) for k,v in anchor.items() if k not in {'start_beat','duration_beats','midi'}}
        generated=[]; cursor=start
        for note_index,(interval,dur) in enumerate(zip(statement['intervals'],statement['rhythm'])):
            scale_steps=int(interval)-source_first
            midi=_move_scale_steps(base_anchor,scale_steps,root,scale)+int(statement['semitone_shift'])
            ev=deepcopy(template)
            ev.update({
                'start_beat':round(cursor,9),
                'duration_beats':round(float(dur)*0.88,9),
                'midi':int(max(0,min(127,midi))),
                'motif_statement':{
                    'statement_id':sid,
                    'source_motif_id':statement['source_motif_id'],
                    'note_index':note_index,
                    'source_interval':source_first if note_index==0 else None,
                    'transformed_interval':int(interval),
                    'semitone_shift':int(statement['semitone_shift']),
                    'identity_score':statement['identity']['score'],
                    'identity_floor':statement['identity_floor'],
                    'identity_hard_min':statement.get('identity_hard_min'),
                    'identity_target_met':statement.get('identity_target_met'),
                    'relation':deepcopy(statement.get('relation')),
                }
            })
            generated.append(ev)
            cursor += float(dur)

        before=len(track.get('events',[]))
        kept=[e for e in track.get('events',[]) if not (start-1e-9 <= float(e.get('start_beat',-1)) < end-1e-9)]
        track['events']=sorted(kept+generated,key=lambda e:(float(e.get('start_beat',0)),int(e.get('midi',0))))
        phrase_reports.append({
            'phrase_id':phrase['phrase_id'],'role':role,'statement_id':sid,
            'removed_event_count':before-len(kept),'generated_event_count':len(generated),
            'identity':deepcopy(statement['identity']),
            'duration_beats':round(total,9),
        })

    out['motif_development_resolved']=True
    out['motif_development_report']={
        'statement_count':len(compiled),
        'realized_phrase_count':len(phrase_reports),
        'statements':[deepcopy(compiled[k]) for k in sorted(compiled)],
        'phrases':phrase_reports,
    }
    return out


__all__=[
    'MotifDevelopmentError','motif_identity_metrics','apply_transform_chain',
    'validate_motif_development_contract','realize_motif_statements'
]
