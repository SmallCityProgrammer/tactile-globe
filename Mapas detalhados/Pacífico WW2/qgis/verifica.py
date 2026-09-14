import os, sys
from qgis.core import QgsApplication, QgsProject
q = QgsApplication([], False); q.initQgis()
p = QgsProject.instance()
ok = p.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pearl-harbor.qgz'))
print('abriu:', ok, '| CRS:', p.crs().authid())
for l in p.layerTreeRoot().layerOrder():
    print(('  OK ' if l.isValid() else '  QUEBRADA ') + l.name().ljust(9), l.featureCount() if l.isValid() else '', os.path.basename(l.source().split('|')[0]))
q.exitQgis()
