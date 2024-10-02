/**
 * originally based on
 *
 * <p>
 * Copyright (C) 2015, GIAYBAC
 * <p>
 * Released under the MIT license
 * <p>
 * heavily modified and extended IBO
 */
package sciscore.key_resource_table_extractor;

import com.giaybac.traprange.TrapRangeBuilder;
import com.google.common.collect.HashMultimap;
import com.google.common.collect.LinkedListMultimap;
import com.google.common.collect.Multimap;
import com.google.common.collect.Range;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.TextPosition;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import sciscore.key_resource_table_extractor.common.Rectangle;
import sciscore.key_resource_table_extractor.common.Table;
import sciscore.key_resource_table_extractor.common.TableCell;
import sciscore.key_resource_table_extractor.common.TableRow;
import sciscore.key_resource_table_extractor.table_transformer.PDFTable;

import java.io.*;
import java.util.*;

/**
 * @author Tho Mar 22, 2015 3:34:29 PM
 * IBO vertical line ranges extracted are used to aid table column detection (Nov 15 2022)
 */
@SuppressWarnings("Duplicates")
public class PDFTableExtractor2 {
    private final Logger logger = LoggerFactory.getLogger(PDFTableExtractor2.class);
    //contains pages that will be extracted table content.
    //If this variable doesn't contain any page, all pages will be extracted
    private final List<Integer> extractedPages = new ArrayList<>();
    private final List<Integer> exceptedPages = new ArrayList<>();
    //contains avoided line idx-s for each page,
    //if this multimap contains only one element and key of this element equals -1
    //then all lines in extracted pages contains in multi-map value will be avoided
    private final Multimap<Integer, Integer> pageNExceptedLinesMap = HashMultimap.create();

    private InputStream inputStream;
    private PDDocument document;
    private String password;

    private String pdfFile;

    public PDFTableExtractor2 setSource(InputStream inputStream) {
        this.inputStream = inputStream;
        return this;
    }

    public PDFTableExtractor2 setSource(InputStream inputStream, String password) {
        this.inputStream = inputStream;
        this.password = password;
        return this;
    }

    public PDFTableExtractor2 setSource(File file) {
        this.pdfFile = file.getAbsolutePath();
        return this;
    }

    public PDFTableExtractor2 setSource(String filePath) {
        this.pdfFile = filePath;
        return this.setSource(new File(filePath));
    }

    public PDFTableExtractor2 setSource(File file, String password) {
        try {
            return this.setSource(new FileInputStream(file), password);
        } catch (FileNotFoundException ex) {
            throw new RuntimeException("Invalid pdf file", ex);
        }
    }

    public PDFTableExtractor2 setSource(String filePath, String password) {
        return this.setSource(new File(filePath), password);
    }

    /**
     * This page will be analyze and extract its table content
     *
     * @param pageIdx
     * @return
     */
    public PDFTableExtractor2 addPage(int pageIdx) {
        extractedPages.add(pageIdx);
        return this;
    }

    public PDFTableExtractor2 exceptPage(int pageIdx) {
        exceptedPages.add(pageIdx);
        return this;
    }

    /**
     * Avoid a specific line in a specific page. LineIdx can be negative number,
     * -1 is the last line
     *
     * @param pageIdx
     * @param lineIdxes
     * @return
     */
    public PDFTableExtractor2 exceptLine(int pageIdx, int[] lineIdxes) {
        for (int lineIdx : lineIdxes) {
            pageNExceptedLinesMap.put(pageIdx, lineIdx);
        }
        return this;
    }

    /**
     * Avoid this line in all extracted pages. LineIdx can be negative number,
     * -1 is the last line
     *
     * @param lineIdxes
     * @return
     */
    public PDFTableExtractor2 exceptLine(int[] lineIdxes) {
        this.exceptLine(-1, lineIdxes);
        return this;
    }

    public Table cleanup(Table table) {
        List<TableRow> toBeRemoved = new ArrayList<>();
        for (TableRow row : table.getRows()) {
            if (isEmpty(row)) {
                toBeRemoved.add(row);
            }
        }
        table.getRows().removeAll(toBeRemoved);

        return table;
    }


    public static boolean isEmpty(TableRow row) {
        for (TableCell cell : row.getCells()) {
            if (cell.getContent().trim().length() > 0) {
                return false;
            }
        }
        return true;
    }


    public static List<Rectangle> filter(List<Rectangle> rectList, Rectangle pageBounds) {
        List<Rectangle> filtered = new ArrayList<>(rectList.size());
        for (Rectangle rect : rectList) {
            if (pageBounds.contains(rect)) {
                filtered.add(rect);
            }
        }
        return filtered;
    }

    public List<Table> extractTableContents(Map<Integer,
            List<PDFTable>> page2PdfTablesMap, boolean useRowInfo) throws Exception {
        List<Table> tables = new ArrayList<>();
        //TODO
        Multimap<Integer, Range<Integer>> pageIdNLineRangesMap = LinkedListMultimap.create();
        Multimap<Integer, TextPosition> pageIdNTextsMap = LinkedListMultimap.create();
        try {
            // this.document = this.password != null ? PDDocument.load(inputStream, this.password) : PDDocument.load(inputStream);
            this.document = this.password != null ? Loader.loadPDF(new File(this.pdfFile), this.password)
                    : Loader.loadPDF(new File(this.pdfFile));
            for (int pageId = 0; pageId < document.getNumberOfPages(); pageId++) {
                List<TextPosition> texts = extractTextPositions(pageId);//sorted by .getY() ASC
                //extract line ranges
                List<Range<Integer>> lineRanges = getLineRanges(pageId, texts);
                //extract column ranges
                List<TextPosition> textsByLineRanges = getTextsByLineRanges(lineRanges, texts);

                pageIdNLineRangesMap.putAll(pageId, lineRanges);
                pageIdNTextsMap.putAll(pageId, textsByLineRanges);
            }
            Map<Integer, Rectangle> pageBoundsMap = PDFUtils.getPageBounds(this.pdfFile);
            for (int pageId : pageIdNTextsMap.keySet()) {
                if (!page2PdfTablesMap.containsKey(pageId)) {
                    continue;
                }
                List<TextPosition> pageContent = (List) pageIdNTextsMap.get(pageId);
                double avgCharWidth = getAverageWidth(pageContent);
                List<PDFTable> pdfTables = page2PdfTablesMap.get(pageId);
                for (PDFTable pdfTable : pdfTables) {
                    Rectangle pageBounds = pageBoundsMap.get(pageId);
                    System.out.println("pageBounds:" + pageBounds);
                    pdfTable.calcScaleFactors((float) pageBounds.getWidth(),
                            (float) pageBounds.getHeight());
                    List<Range<Integer>> colRanges = pdfTable.getColumnRanges();
                    // expand last column range for 2 average character width to
                    // compensate for the tight Table Transformer detected boundaries
                    colRanges = expandLastColumnRange(colRanges, avgCharWidth * 2);
                    List<Range<Integer>> rowLineRanges = (List<Range<Integer>>) pageIdNLineRangesMap.get(pageId);

                    if (useRowInfo) {
                        rowLineRanges = pdfTable.getRowRanges();
                    }
                    Table table = buildTable3(pageId, pageContent,
                            (List) pageIdNLineRangesMap.get(pageId),
                            colRanges, pdfTable.getBounds(),
                            rowLineRanges);
                    tables.add(table);

                    logger.debug("Found " + table.getRows().size() + " row(s) and " + colRanges.size()
                            + " column(s) of a table in page " + pageId);
                }
            }
        } catch (IOException ex) {
            throw new RuntimeException("Parse pdf file fail", ex);
        } finally {
            if (this.document != null) {
                try {
                    this.document.close();
                } catch (IOException ex) {
                    logger.error(null, ex);
                }
            }
        }

        return tables;
    }

    public static List<Range<Integer>> expandLastColumnRange(List<Range<Integer>> colRanges, double expandAmount) {
        Range<Integer> lastColRange = colRanges.get(colRanges.size() - 1);
        Range<Integer> newColRange = Range.closed(lastColRange.lowerEndpoint(),
                (int) (lastColRange.upperEndpoint() + expandAmount));
        colRanges.set(colRanges.size() - 1, newColRange);
        return colRanges;
    }


    private void showRowColTrapRanges(List<Range<Integer>> rowTrapRanges,
                                      List<Range<Integer>> columnTrapRanges) {
        // IBO
        System.out.println("Column Trap Ranges");
        for (Range<Integer> range : columnTrapRanges) {
            System.out.println(range.toString());
        }
        System.out.println("-----------------------");
        System.out.println("Row Trap Ranges");
        for (Range<Integer> range : rowTrapRanges) {
            System.out.println(range.toString());
        }
        System.out.println("-----------------------");
    }


    private Table buildTable3(int pageIdx, List<TextPosition> tableContent,
                              List<Range<Integer>> rowTrapRanges,
                              List<Range<Integer>> columnTrapRanges,
                              Rectangle enclosing,
                              List<Range<Integer>> rowLineRanges) {
        Table table = new Table(pageIdx, columnTrapRanges.size());
        int idx = 0;
        int rowIdx = 0;
        // IBO
        if (logger.isDebugEnabled()) {
            showRowColTrapRanges(rowTrapRanges, columnTrapRanges);
        }
        List<TextPosition> rowContent = new ArrayList<>();
        Map<TableRow, Range<Integer>> row2rowTrapMap = new HashMap<>();

        StringBuilder outside = new StringBuilder();
        while (idx < tableContent.size()) {
            TextPosition textPosition = tableContent.get(idx);
            if (!enclosing.contains(textPosition.getX(), textPosition.getY())) {
                outside.append(textPosition.getUnicode());
                idx++;
                continue;
            }
            if (outside.length() > 0) {
                System.out.println("outside: " + outside);
                outside.setLength(0);
            }
            Range<Integer> rowTrapRange = rowTrapRanges.get(rowIdx);
            Range<Integer> textRange = Range.closed((int) textPosition.getY(),
                    (int) (textPosition.getY() + textPosition.getHeight()));

            if (rowTrapRange.encloses(textRange)) {
                rowContent.add(textPosition);
                idx++;
            } else {
                TableRow row = buildRow(rowIdx, rowContent, columnTrapRanges);
                row2rowTrapMap.put(row, rowTrapRange);
                table.getRows().add(row);
                //next row: clear rowContent
                rowContent.clear();
                rowIdx++;
            }
        }
        //last row
        if (!rowContent.isEmpty() && rowIdx < rowTrapRanges.size()) {
            TableRow row = buildRow(rowIdx, rowContent, columnTrapRanges);
            table.getRows().add(row);
        }
        // merge phase
        Table table2 = new Table(pageIdx, columnTrapRanges.size());
        int trIdx = 0;
        List<TableRow> rows = table.getRows();
        rowIdx = 0;
        for (Range<Integer> rowLineRange : rowLineRanges) {
            List<TableRow> toBeMerged = new ArrayList<>(3);
            while (trIdx < rows.size()) {
                TableRow row = rows.get(trIdx);

                Range<Integer> rowTrapRange = row2rowTrapMap.get(row);
                if (rowTrapRange == null) {
                    boolean hasEmptyCells = hasEmptyColumns(row);
                    if (!toBeMerged.isEmpty()) {
                        if (hasEmptyCells) {
                            // most probably part of a multiline row
                            toBeMerged.add(row);
                        }
                        TableRow tableRow = mergeRows(toBeMerged, rowIdx);
                        table2.getRows().add(tableRow);
                        toBeMerged.clear();
                    }
                    // last row
                    // FIXME remove this heuristic IBO 07/23/2024
                    if (!hasEmptyCells) {
                        toBeMerged.add(row);
                    }
                    trIdx++;
                    break;
                }

                if (canBeMerged(rowTrapRange, rowLineRange, row)) {
                    toBeMerged.add(row);
                    trIdx++;
                } else {
                    if (rowTrapRange.upperEndpoint() < rowLineRange.lowerEndpoint()) {
                        trIdx++;
                    } else {
                        break;
                    }
                }
            }
            if (!toBeMerged.isEmpty()) {
                TableRow tableRow = mergeRows(toBeMerged, rowIdx);
                table2.getRows().add(tableRow);
                rowIdx++;
            } else {
                trIdx++;
            }
        }
        return table2;
    }

    public static boolean hasEmptyColumns(TableRow row) {
        for (TableCell cell : row.getCells()) {
            if (cell.getContent().trim().isEmpty()) {
                return true;
            }
        }
        return false;
    }


    public static boolean canBeMerged(Range<Integer> first, Range<Integer> second, TableRow row) {
        if (second.encloses(first)) {
            return true;
        }
        double ratio = Utils.overlapRatio(first, second);
        boolean emptyColumns = hasEmptyColumns(row);
        if (ratio >= 0.7) {
            return true;
        }
        if (ratio > 0.5 && emptyColumns) {
            return true;
        }

        return false;
    }


    public static TableRow mergeRows(List<TableRow> rows, int idx) {
        TableRow newRow = new TableRow(idx);
        int noCells = 0;
        for (TableRow row : rows) {
            if (row.getCells().size() > noCells) {
                noCells = row.getCells().size();
            }
        }

        for (int i = 0; i < noCells; i++) {
            StringBuilder sb = new StringBuilder(80);
            for (TableRow row : rows) {
                if (i < row.getCells().size()) {
                    sb.append(row.getCells().get(i).getContent());
                }
            }
            String content = sb.toString().trim();
            TableCell newCell = new TableCell(i, content);
            newRow.getCells().add(newCell);
        }
        return newRow;
    }


    /**
     * @param rowIdx
     * @param rowContent
     * @param columnTrapRanges
     * @return
     */
    private TableRow buildRow(int rowIdx, List<TextPosition> rowContent,
                              List<Range<Integer>> columnTrapRanges) {
        TableRow retVal = new TableRow(rowIdx);
        //Sort rowContent
        Collections.sort(rowContent, (o1, o2) -> {
            int retVal1 = 0;
            if (o1.getX() < o2.getX()) {
                retVal1 = -1;
            } else if (o1.getX() > o2.getX()) {
                retVal1 = 1;
            }
            return retVal1;
        });

        int idx = 0;
        int columnIdx = 0;
        List<TextPosition> cellContent = new ArrayList<>();
        while (idx < rowContent.size()) {
            TextPosition textPosition = rowContent.get(idx);
            if (columnIdx >= columnTrapRanges.size()) {
                ++idx;
                continue;
            }
            Range<Integer> columnTrapRange = columnTrapRanges.get(columnIdx);
            Range<Integer> textRange = Range.closed((int) textPosition.getX(),
                    (int) (textPosition.getX() + textPosition.getWidth()));
            if (columnTrapRange.encloses(textRange)) {
                cellContent.add(textPosition);
                idx++;
            } else {
                TableCell cell = buildCell(columnIdx, cellContent);
                retVal.getCells().add(cell);
                //next column: clear cell content
                cellContent.clear();
                columnIdx++;
            }
        }
        if (!cellContent.isEmpty() && columnIdx < columnTrapRanges.size()) {
            TableCell cell = buildCell(columnIdx, cellContent);
            retVal.getCells().add(cell);
        }
        //return
        return retVal;
    }


    public static double getMaxHeight(List<TextPosition> tpList) {
        if (tpList.isEmpty()) {
            return 0;
        }
        double max = 0;
        for (TextPosition tp : tpList) {
            if (tp.getHeight() > max) {
                max = tp.getHeight();
            }
        }
        return max;
    }

    public static double getAverageWidth(List<TextPosition> tpList) {
        if (tpList.isEmpty()) {
            return 0;
        }
        double sum = 0;
        for (TextPosition tp : tpList) {
            sum += tp.getWidth();
        }
        return sum / tpList.size();
    }

    public static String toText(List<TextPosition> cellContent) {
        StringBuilder sb = new StringBuilder();
        for (TextPosition textPosition : cellContent) {
            sb.append(textPosition.getUnicode());
        }
        return sb.toString();
    }

    private TableCell buildCell(int columnIdx, List<TextPosition> cellContent) {
        Collections.sort(cellContent, (o1, o2) -> {
            int retVal = 0;
            if (o1.getX() < o2.getX()) {
                retVal = -1;
            } else if (o1.getX() > o2.getX()) {
                retVal = 1;
            }
            return retVal;
        });
        String content = toText(cellContent);
        // sort by Y coordinate also (for multiline cells)
        // allowing for super and subscripts IBO
        // double avgHeight = getAverageHeight(cellContent); // orig
        double avgHeight = getMaxHeight(cellContent);
        // double threshold = 0.7 * avgHeight; // orig
        double threshold = 0.7 * avgHeight;

        Collections.sort(cellContent, (o1, o2) -> {
            double dist = Math.abs(o1.getY() - o2.getY());
            if (dist <= threshold) {
                return 0;
            } else {
                if (o1.getY() < o2.getY()) {
                    return -1; // was 1
                } else if (o1.getY() > o2.getY()) {
                    return 1;
                }
            }
            return 0;
        });
        StringBuilder cellContentBuilder = new StringBuilder();
        for (TextPosition textPosition : cellContent) {
            cellContentBuilder.append(textPosition.getUnicode());
        }
        String cellContentString = cellContentBuilder.toString();
        Rectangle bounds = getBounds(cellContent);
        return new TableCell(columnIdx, cellContentString, bounds);
    }

    public static Rectangle getBounds(List<TextPosition> cellContent) {
        double minX = Double.MAX_VALUE, minY = Double.MAX_VALUE;
        double maxX = -1, maxY = -1;
        for (TextPosition tp : cellContent) {
            if (tp.getX() < minX) {
                minX = tp.getX();
            }
            if (tp.getY() < minY) {
                minY = tp.getY();
            }
            if (tp.getX() + tp.getWidth() > maxX) {
                maxX = tp.getX() + tp.getWidth();
            }
            if (tp.getY() + tp.getHeight() > maxY) {
                maxY = tp.getY() + tp.getHeight();
            }
        }
        return new Rectangle((float) minY, (float) minX,
                (float) (maxX - minX),
                (float) (maxY - minY));
    }


    private List<TextPosition> extractTextPositions(int pageId) throws IOException {
        TextPositionExtractor extractor = new TextPositionExtractor(document, pageId);
        return extractor.extract();
    }

    private boolean isExceptedLine(int pageIdx, int lineIdx) {
        boolean retVal = this.pageNExceptedLinesMap.containsEntry(pageIdx, lineIdx)
                || this.pageNExceptedLinesMap.containsEntry(-1, lineIdx);
        return retVal;
    }

    /**
     * Remove all texts in excepted lines
     * <p>
     * TexPositions are sorted by .getY() ASC
     *
     * @param lineRanges
     * @param textPositions
     * @return
     */
    private List<TextPosition> getTextsByLineRanges(List<Range<Integer>> lineRanges, List<TextPosition> textPositions) {
        List<TextPosition> retVal = new ArrayList<>();
        int idx = 0;
        int lineIdx = 0;
        while (idx < textPositions.size() && lineIdx < lineRanges.size()) {
            TextPosition textPosition = textPositions.get(idx);
            Range<Integer> textRange = Range.closed((int) textPosition.getY(),
                    (int) (textPosition.getY() + textPosition.getHeight()));
            Range<Integer> lineRange = lineRanges.get(lineIdx);
            if (lineRange.encloses(textRange)) {
                retVal.add(textPosition);
                idx++;
            } else if (lineRange.upperEndpoint() < textRange.lowerEndpoint()) {
                lineIdx++;
            } else {
                idx++;
            }
        }
        return retVal;
    }

    private List<List<TextPosition>> toRows(List<TextPosition> texts) {
        List<List<TextPosition>> rowTexts = new ArrayList<>();
        Collections.sort(texts, (o1, o2) -> {
            if (o1.getY() > o2.getY()) {
                return 1;
            } else if (o1.getY() < o2.getY()) {
                return -1;
            }
            return 0;
        });
        TextPosition prev = null;
        List<TextPosition> row = null;
        for (TextPosition tp : texts) {
            if (prev == null || prev.getY() != tp.getY()) {
                prev = tp;
                row = new ArrayList<>();
                rowTexts.add(row);
            }
            row.add(tp);
        }

        return rowTexts;
    }


    public void showRow(List<TextPosition> row) {
        StringBuilder sb = new StringBuilder();
        for (TextPosition tp : row) {
            sb.append(tp.getUnicode());
        }
        System.out.println(sb.toString());
    }

    private List<Range<Integer>> getLineRanges(int pageId, List<TextPosition> pageContent) {
        TrapRangeBuilder lineTrapRangeBuilder = new TrapRangeBuilder();
        for (TextPosition textPosition : pageContent) {
            Range<Integer> lineRange = Range.closed((int) textPosition.getY(),
                    (int) (textPosition.getY() + textPosition.getHeight()));
            //add to builder
            lineTrapRangeBuilder.addRange(lineRange);
        }
        List<Range<Integer>> lineTrapRanges = lineTrapRangeBuilder.build();
        List<Range<Integer>> retVal = removeExceptedLines(pageId, lineTrapRanges);
        return retVal;
    }

    private List<Range<Integer>> removeExceptedLines(int pageIdx, List<Range<Integer>> lineTrapRanges) {
        List<Range<Integer>> retVal = new ArrayList<>();
        for (int lineIdx = 0; lineIdx < lineTrapRanges.size(); lineIdx++) {
            boolean isExceptedLine = isExceptedLine(pageIdx, lineIdx)
                    || isExceptedLine(pageIdx, lineIdx - lineTrapRanges.size());
            if (!isExceptedLine) {
                retVal.add(lineTrapRanges.get(lineIdx));
            }
        }
        return retVal;
    }

}
