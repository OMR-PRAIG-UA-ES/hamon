# Generated from hamonParser.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .hamonParser import hamonParser
else:
    from hamonParser import hamonParser

# This class defines a complete generic visitor for a parse tree produced by hamonParser.

class hamonParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by hamonParser#start.
    def visitStart(self, ctx:hamonParser.StartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#line.
    def visitLine(self, ctx:hamonParser.LineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#versionDecl.
    def visitVersionDecl(self, ctx:hamonParser.VersionDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#systemDecl.
    def visitSystemDecl(self, ctx:hamonParser.SystemDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#harmonyGroup.
    def visitHarmonyGroup(self, ctx:hamonParser.HarmonyGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#positionItem.
    def visitPositionItem(self, ctx:hamonParser.PositionItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#harmonyList.
    def visitHarmonyList(self, ctx:hamonParser.HarmonyListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#harmony.
    def visitHarmony(self, ctx:hamonParser.HarmonyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#harmonyAtom.
    def visitHarmonyAtom(self, ctx:hamonParser.HarmonyAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#layerTag.
    def visitLayerTag(self, ctx:hamonParser.LayerTagContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#analysisAttr.
    def visitAnalysisAttr(self, ctx:hamonParser.AnalysisAttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#attrItem.
    def visitAttrItem(self, ctx:hamonParser.AttrItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#noChord.
    def visitNoChord(self, ctx:hamonParser.NoChordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#functionalHarmony.
    def visitFunctionalHarmony(self, ctx:hamonParser.FunctionalHarmonyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#funcToken.
    def visitFuncToken(self, ctx:hamonParser.FuncTokenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#funcSingleToken.
    def visitFuncSingleToken(self, ctx:hamonParser.FuncSingleTokenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#meterDecl.
    def visitMeterDecl(self, ctx:hamonParser.MeterDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#keyDecl.
    def visitKeyDecl(self, ctx:hamonParser.KeyDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#keyTarget.
    def visitKeyTarget(self, ctx:hamonParser.KeyTargetContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#modeSuffix.
    def visitModeSuffix(self, ctx:hamonParser.ModeSuffixContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#scaleDecl.
    def visitScaleDecl(self, ctx:hamonParser.ScaleDeclContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#scaleName.
    def visitScaleName(self, ctx:hamonParser.ScaleNameContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#chordSymbol.
    def visitChordSymbol(self, ctx:hamonParser.ChordSymbolContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#pitch.
    def visitPitch(self, ctx:hamonParser.PitchContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#accidental.
    def visitAccidental(self, ctx:hamonParser.AccidentalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#slashBass.
    def visitSlashBass(self, ctx:hamonParser.SlashBassContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#chordPart.
    def visitChordPart(self, ctx:hamonParser.ChordPartContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#qualityMark.
    def visitQualityMark(self, ctx:hamonParser.QualityMarkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#seventhMark.
    def visitSeventhMark(self, ctx:hamonParser.SeventhMarkContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#extension.
    def visitExtension(self, ctx:hamonParser.ExtensionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#alteration.
    def visitAlteration(self, ctx:hamonParser.AlterationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#addOmitSus.
    def visitAddOmitSus(self, ctx:hamonParser.AddOmitSusContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#parenGroup.
    def visitParenGroup(self, ctx:hamonParser.ParenGroupContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#parenItem.
    def visitParenItem(self, ctx:hamonParser.ParenItemContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#romanNumeral.
    def visitRomanNumeral(self, ctx:hamonParser.RomanNumeralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#rnAccidental.
    def visitRnAccidental(self, ctx:hamonParser.RnAccidentalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#rnTail.
    def visitRnTail(self, ctx:hamonParser.RnTailContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#rnSecondary.
    def visitRnSecondary(self, ctx:hamonParser.RnSecondaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#numberHarmony.
    def visitNumberHarmony(self, ctx:hamonParser.NumberHarmonyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#numberTail.
    def visitNumberTail(self, ctx:hamonParser.NumberTailContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#numberSecondary.
    def visitNumberSecondary(self, ctx:hamonParser.NumberSecondaryContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#textLabel.
    def visitTextLabel(self, ctx:hamonParser.TextLabelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#rawRun.
    def visitRawRun(self, ctx:hamonParser.RawRunContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by hamonParser#rawAtom.
    def visitRawAtom(self, ctx:hamonParser.RawAtomContext):
        return self.visitChildren(ctx)



del hamonParser