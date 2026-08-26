
from jarvis.db.figshare import data
from jarvis.core.atoms import Atoms
from jarvis.io.vasp.inputs import Poscar

jid = "JVASP-98550"  # replace with a valid JID from your dataset

records = data("dft_3d")

matches = [r for r in records if r.get("jid") == jid]

if not matches:
    print(f"No record found for {jid}")
    print("First 20 available JIDs:")
    for r in records[:20]:  
        print(r.get("jid"), r.get("formula"))
    raise SystemExit(1)

record = matches[0]

atoms_dict = record["atoms"]
atoms = Atoms.from_dict(atoms_dict)

print("Found:", record.get("jid"), record.get("formula"))
print("Atoms type:", type(atoms))

out_file = f"POSCAR_{jid}"
Poscar(atoms).write_file(out_file)

print(f"Wrote {out_file}")
