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

    renamedClasses = 0
    renamedPackages = 0

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

                self.deal_one_class(unit,fullName,clazz)
                self.rename_superclasses_and_interfaces(unit,clazz,dv2)
        print("Classes renamed count : " + str(self.renamedClasses))
        print("Packages renamed count : " + str(self.renamedPackages))

    def rename_superclasses_and_interfaces(self,unit,clazz,dv2):
        superTypes = clazz.getSupertypes()
        interfaces = clazz.getImplementedInterfaces()
        count = len(superTypes) + len(interfaces)
        address = superTypes[0].getAddress()
        noSuperClass = False
        if address == "Ljava/lang/Object;":
            count -= 1
            noSuperClass = True
        
        if count == 1:
            if not noSuperClass:
                if superTypes[0].isRenamed():
                    return
                address = superTypes[0].getAddress()
                if address.startswith("Ljava"):
                    return
                
                fullName = str(unit.getString(dv2[1].getStringIndex()))
                if address == fullName:
                    return
                
                if len(address.split("/")) == len(fullName.split("/")):
                    self.deal_one_class(unit,fullName,superTypes[0].getImplementingClass())
            else:
                if interfaces[0].isRenamed():
                    return
                address = interfaces[0].getAddress()
                if address.startswith("Ljava"):
                    return
                
                fullName = str(unit.getString(dv2[1].getStringIndex()))
                if address == fullName:
                    return
                
                if len(address.split("/")) == len(fullName.split("/")):
                    self.deal_one_class(unit,fullName,interfaces[0].getImplementingClass())

        if count > 1:
            total = superTypes + interfaces
            stringList = map(lambda s:str(unit.getString(s.getStringIndex())),list(dv2)[1:len(total)])

            for s in stringList:
                if len(s.split("/")) == 1:
                    return

            if total[0].getAddress() == "Ljava/lang/Object;":
                total = total[1:len(total)]
            if len(total) != len(stringList):
                return

            toDeal = None
            matchedString = []
            for clz in total:
                address = clz.getAddress()
                isMatch = False
                for fullName in stringList:
                    if(fullName == address):
                        isMatch = True
                        matchedString.append(fullName)
                        break
    
                if isMatch:
                    continue
                if toDeal:
                    return
                toDeal = clz

            for s in matchedString:
                stringList.remove(s)
            if len(stringList) != 1:
                return

            print(toDeal.getAddress())
            print("rename : " + stringList[0])
            self.deal_one_class(unit,stringList[0],toDeal.getImplementingClass())

    def deal_one_class(self,unit,fullName,clazz):
        if clazz.isRenamed():
            return
        if fullName.find("/") == -1:
            return
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
            if elements[0].getValue().getType() != 28 or elements[1].getValue().getType() != 28 or elements[2].getValue().getType() != 28 or elements[3].getValue().getType() != 4 or elements[4].getValue().getType() != 28:
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
        if originClazz.isRenamed():
            return
        actCtx = ActionContext(unit, Actions.RENAME, originClazz.getItemId(), originClazz.getAddress())
        actData = ActionRenameData()
        actData.setNewName(sourceName)

        if unit.prepareExecution(actCtx, actData):
            try:
                result = unit.executeAction(actCtx, actData)
                if result:
                    self.renamedClasses += 1
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
                    self.renamedPackages += 1
                else:
                    print('package rename to %s failed!' % sourceName)
            except Exception, e:
                print (Exception, e)