from com.pnfsoftware.jeb.client.api import IScript
from com.pnfsoftware.jeb.core import RuntimeProjectUtil
from com.pnfsoftware.jeb.core.units.code import ICodeUnit, ICodeItem
from com.pnfsoftware.jeb.core.units.code.android import IDexUnit
from com.pnfsoftware.jeb.core.actions import Actions, ActionContext, ActionCommentData, ActionRenameData
from java.lang import Runnable

class KotlinRename(IScript):
  def run(self, ctx):
        ctx.executeAsync("Running deobscure class ...", JEB2AutoRename(ctx))
        print('Done')

class JEB2AutoRename(Runnable):
    def __init__(self, ctx):
        self.ctx = ctx

    def run(self):
        ctx = self.ctx
        engctx = ctx.getEnginesContext()
        if not engctx:
            print('Back-end engines not initialized')
            return

        projects = engctx.getProjects()
        if not projects:
            print('There is no opened project')
            return

        prj = projects[0]

        units = RuntimeProjectUtil.findUnitsByType(prj, IDexUnit, False)

        for unit in units:
            classes = unit.getClasses()
            for clazz in classes:
                
                #find all dv2 of Kotlin Metadata
                dv2 = self.find_metadata_annotation(clazz)

                if not dv2:
                    continue
                fullName = str(unit.getString(dv2[0].getStringIndex()))
                if fullName.find("/") == -1:
                    continue
                li = fullName.split("/")
                li.reverse()

                name = li[0]
                if name.find(";") != -1:
                    name = name[0:len(name)-1]
                
                package = clazz.getPackage()

                for i in range(1,len(li)):
                    newName = li[i]
                    if (i == len(li)-1) & (newName[0] == 'L'):
                        newName = newName[1:len(newName)]
                    self.rename_package(unit, package, newName)
                    package = package.getParentPackage()

                #self.comment_class(unit, clazz, clazz.getName(True))  # Backup origin clazz name to comment
                self.rename_class(unit, clazz, name, True)  # Rename to source name

    def find_metadata_annotation(self,clazz):
        annotationsDirectory = clazz.getAnnotationsDirectory()
        if not annotationsDirectory:
            return None

        annos = annotationsDirectory.getClassAnnotations()
        for anno in annos:
            if anno.formatVisibility() != "runtime":
                continue
            annotation = anno.getAnnotation()
            elements = annotation.getElements()
            if len(elements) != 5:
                continue
            if elements[0].getValue().getType() != 28 | elements[1].getValue().getType() != 28 | elements[2].getValue().getType() != 28 | elements[3].getValue().getType() != 4 | elements[4].getValue().getType() != 28:
                continue
            dv2 = elements[2].getValue().getArray()
            return dv2
        return None

    def comment_class(self, unit, originClazz, commentStr):
        actCtx = ActionContext(unit, Actions.COMMENT, originClazz.getItemId(), originClazz.getAddress())
        actData = ActionCommentData()
        actData.setNewComment(commentStr)

        if unit.prepareExecution(actCtx, actData):
            try:
                result = unit.executeAction(actCtx, actData)
                if result:
                    print('comment to %s success!' % commentStr)
                else:
                    print('comment to %s failed!' % commentStr)
            except Exception, e:
                print (Exception, e)

    def rename_class(self, unit, originClazz, sourceName, isBackup):
        actCtx = ActionContext(unit, Actions.RENAME, originClazz.getItemId(), originClazz.getAddress())
        actData = ActionRenameData()
        actData.setNewName(sourceName)

        if unit.prepareExecution(actCtx, actData):
            try:
                result = unit.executeAction(actCtx, actData)
                if result:
                    print('class rename to %s success!' % sourceName)
                else:
                    print('class rename to %s failed!' % sourceName)
            except Exception, e:
                print (Exception, e)

    def rename_package(self, unit, package, sourceName):
        actCtx = ActionContext(unit, Actions.RENAME, package.getItemId(), package.getAddress())
        actData = ActionRenameData()
        actData.setNewName(sourceName)

        if unit.prepareExecution(actCtx, actData):
            try:
                result = unit.executeAction(actCtx, actData)
                if result:
                    print('package rename to %s success!' % sourceName)
                else:
                    print('package rename to %s failed!' % sourceName)
            except Exception, e:
                print (Exception, e)