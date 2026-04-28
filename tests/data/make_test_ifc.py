"""
Generates minimal IFC test files using ifcopenshell model building API.
Run once: python tests/data/make_test_ifc.py
"""
import sys
from pathlib import Path

try:
    import ifcopenshell
    import ifcopenshell.api
    import ifcopenshell.api.root
    import ifcopenshell.api.unit
    import ifcopenshell.api.context
    import ifcopenshell.api.project
    import ifcopenshell.api.geometry
    import ifcopenshell.api.spatial
    import ifcopenshell.api.aggregate
    import ifcopenshell.util.element
except ImportError:
    print("ifcopenshell not available; generating stub IFC files via raw STEP-21 syntax")
    _write_stub_ifc()
    sys.exit(0)


def _write_stub_ifc() -> None:
    """Write minimal hand-crafted IFC STEP-21 files without ifcopenshell."""
    out = Path(__file__).parent

    # Simple rectangular slab 10x6 m, no openings
    simple = out / "simple_slab.ifc"
    simple.write_text(
        """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('simple_slab.ifc','2026-04-28',('Daud Tasleem'),(''),
  'IfcOpenShell','ifc-slab-mesh test','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0001',$,'TestProject',$,$,$,$,#2,#3);
#2=IFCOWNERHISTORY($,$,$,.ADDED.,$,$,$,0);
#3=IFCUNITASSIGNMENT((#4));
#4=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#5=IFCAXIS2PLACEMENT3D(#6,$,$);
#6=IFCCARTESIANPOINT((0.,0.,0.));
#7=IFCLOCALPLACEMENT($,#5);
#8=IFCAXIS2PLACEMENT2D(#9,$);
#9=IFCCARTESIANPOINT((0.,0.));
#10=IFCRECTANGLEPROFILEDEF(.AREA.,'SlabProfile',#8,10.,6.);
#11=IFCAXIS2PLACEMENT3D(#12,#13,#14);
#12=IFCCARTESIANPOINT((0.,0.,0.));
#13=IFCDIRECTION((0.,0.,1.));
#14=IFCDIRECTION((1.,0.,0.));
#15=IFCEXTRUDEDAREASOLID(#10,#11,#13,0.3);
#16=IFCSHAPEREPRESENTATION(#17,'Body','SweptSolid',(#15));
#17=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-05,#5,$);
#18=IFCPRODUCTDEFINITIONSHAPE($,$,(#16));
#19=IFCSLAB('SimpleSlab01',$,'SimpleSlab',$,$,#7,#18,$,.FLOOR.);
ENDSEC;
END-ISO-10303-21;
""",
        encoding="utf-8",
    )
    print(f"Wrote {simple}")

    # Slab with rectangular opening 2x2 m at centre
    with_opening = out / "slab_with_opening.ifc"
    with_opening.write_text(
        """ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('slab_with_opening.ifc','2026-04-28',('Daud Tasleem'),(''),
  'IfcOpenShell','ifc-slab-mesh test','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#1=IFCPROJECT('0002',$,'TestProject',$,$,$,$,#2,#3);
#2=IFCOWNERHISTORY($,$,$,.ADDED.,$,$,$,0);
#3=IFCUNITASSIGNMENT((#4));
#4=IFCSIUNIT(*,.LENGTHUNIT.,$,.METRE.);
#5=IFCAXIS2PLACEMENT3D(#6,$,$);
#6=IFCCARTESIANPOINT((0.,0.,0.));
#7=IFCLOCALPLACEMENT($,#5);
#8=IFCAXIS2PLACEMENT2D(#9,$);
#9=IFCCARTESIANPOINT((0.,0.));
#10=IFCRECTANGLEPROFILEDEF(.AREA.,'SlabProfile',#8,10.,6.);
#11=IFCAXIS2PLACEMENT3D(#12,#13,#14);
#12=IFCCARTESIANPOINT((0.,0.,0.));
#13=IFCDIRECTION((0.,0.,1.));
#14=IFCDIRECTION((1.,0.,0.));
#15=IFCEXTRUDEDAREASOLID(#10,#11,#13,0.3);
#16=IFCSHAPEREPRESENTATION(#17,'Body','SweptSolid',(#15));
#17=IFCGEOMETRICREPRESENTATIONCONTEXT($,'Model',3,1.0E-05,#5,$);
#18=IFCPRODUCTDEFINITIONSHAPE($,$,(#16));
#19=IFCSLAB('SlabWithOpening01',$,'SlabWithOpening',$,$,#7,#18,$,.FLOOR.);
#20=IFCAXIS2PLACEMENT2D(#21,$);
#21=IFCCARTESIANPOINT((0.,0.));
#22=IFCRECTANGLEPROFILEDEF(.AREA.,'OpeningProfile',#20,2.,2.);
#23=IFCEXTRUDEDAREASOLID(#22,#11,#13,0.4);
#24=IFCSHAPEREPRESENTATION(#17,'Body','SweptSolid',(#23));
#25=IFCPRODUCTDEFINITIONSHAPE($,$,(#24));
#26=IFCLOCALPLACEMENT(#7,#27);
#27=IFCAXIS2PLACEMENT3D(#28,$,$);
#28=IFCCARTESIANPOINT((0.,0.,0.));
#29=IFCOPENINGELEMENT('Opening01',$,'Opening',$,$,#26,#25,$);
#30=IFRELVOIDSELEMENT('Rel01',$,$,$,#19,#29);
ENDSEC;
END-ISO-10303-21;
""",
        encoding="utf-8",
    )
    print(f"Wrote {with_opening}")


_write_stub_ifc()
