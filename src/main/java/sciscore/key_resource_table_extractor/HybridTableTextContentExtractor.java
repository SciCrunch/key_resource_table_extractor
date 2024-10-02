package sciscore.key_resource_table_extractor;

import org.apache.commons.cli.*;
import org.json.JSONArray;
import org.json.JSONObject;
import sciscore.key_resource_table_extractor.common.CharSetEncoding;
import sciscore.key_resource_table_extractor.common.Table;
import sciscore.key_resource_table_extractor.table_transformer.PDFTable;

import java.io.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class HybridTableTextContentExtractor {

    public static int extractPageNumber(String filename) {
        Pattern p = Pattern.compile(".+_page_(\\d+)_.+\\.json");
        Matcher matcher = p.matcher(filename);
        if (matcher.find()) {
            try {
                return Integer.parseInt(matcher.group(1));
            } catch(NumberFormatException nfe) {
                nfe.printStackTrace();
            }
        }
        return -1;
    }

    public static int toInt(String number, int defaultNum) {
        try {
            return Integer.parseInt(number);
        } catch(NumberFormatException nfe) {
            return defaultNum;
        }
    }

    public static void orderByPageAndTable(List<File> jsonTableStructFiles) {
        final Pattern p = Pattern.compile(".+_page_(\\d+)_table_(\\d+).+");
        jsonTableStructFiles.sort((o1, o2) -> {
            String name1 = o1.getName();
            String name2 = o2.getName();
            Matcher m1 = p.matcher(name1);
            Matcher m2 = p.matcher(name2);
            if (m1.find() && m2.find()) {
                int page1 = toInt(m1.group(1), -1);
                int table1 = toInt(m1.group(2), -1);
                int page2 = toInt(m2.group(1), -1);
                int table2 = toInt(m2.group(2), -1);
                int cmp = Integer.compare(page1, page2);
                if (cmp == 0) {
                    return Integer.compare(table1, table2);
                }
                return cmp;
            }
            return 0;
        });
    }

    public static Map<Integer, List<PDFTable>> preparePage2PdfTablesMap(List<File> structJsonFiles) throws IOException {
        Map<Integer, List<PDFTable>> page2PdfTablesMap = new HashMap<>();
        for(File structJsonFile : structJsonFiles) {
            int pageNum = extractPageNumber(structJsonFile.getName()); // 1 based
            String jsonStr = FileUtils.loadAsString(structJsonFile.getAbsolutePath(), CharSetEncoding.UTF8);
            JSONObject json = new JSONObject(jsonStr);
            PDFTable table = PDFTable.fromJSON(json);
            Integer pageNo = pageNum -1;
            if (!page2PdfTablesMap.containsKey(pageNo)) {
                page2PdfTablesMap.put(pageNo, new ArrayList<>(1));
            }
            page2PdfTablesMap.get(pageNo).add(table);
        }
        return page2PdfTablesMap;
    }

    public static JSONObject extractTablesAsJSON(String pdfFile, String reportFile,
                                                 Map<Integer, List<PDFTable>> page2PDFTablesMap,
                                                 boolean useRowInfo) throws Exception{
        PDFTableExtractor2 extractor = (new PDFTableExtractor2())
                .setSource(pdfFile);
        List<Table> tables = extractor.extractTableContents(page2PDFTablesMap, useRowInfo);

        Writer writer = null;
        JSONObject json = new JSONObject();
        JSONArray pages = new JSONArray();
        json.put("pages", pages);
        JSONObject pageJson = null;
        int curPageIdx = -1;
        try {
            for (Table table : tables) {
                int pageIdx = table.getPageIdx() + 1;
                if (pageIdx != curPageIdx) {
                    pageJson = new JSONObject().put("page", pageIdx);
                    pageJson.put("tables", new JSONArray());
                    pages.put(pageJson);
                    curPageIdx = pageIdx;
                }
                JSONArray pageTables = pageJson.getJSONArray("tables");
                pageTables.put( table.toJSON() );
            }
            writer = new OutputStreamWriter(new FileOutputStream(reportFile), "UTF-8");
            writer.write(json.toString(2));
            System.out.println("wrote report file: " + reportFile);
            return json;
        } finally {
            FileUtils.close(writer);
        }
    }

    public static void usage(Options options) {
        HelpFormatter formatter = new HelpFormatter();
        formatter.printHelp("HybridTableTextContentExtractor", options);
        System.exit(1);
    }

    public static void main(String[] args) throws Exception {
        Option help = new Option("h", "print this message");
        Option inOption = Option.builder("i").required().hasArg()
                .argName("pdf-file").desc("path to the input PDF file").build();
        Option sDirOption = Option.builder("s").required().hasArg()
                .argName("structure-json-files-dir")
                .desc("path to the structure JSON structure files dir").build();
        Option outJsonFileOption = Option.builder("o").required().hasArg()
                .argName("out-json-file").desc("").build();
        Option useRowInfoOption = Option.builder("r")
                .desc("if set use row info from TableFormer").build();

        Options options = new Options();
        options.addOption(help);
        options.addOption(inOption);
        options.addOption(sDirOption);
        options.addOption(outJsonFileOption);
        options.addOption(useRowInfoOption);

        CommandLineParser cli = new DefaultParser();
        CommandLine line = null;
        try {
            line = cli.parse(options, args);
        } catch (Exception x) {
            System.err.println(x.getMessage());
            usage(options);
        }

        if (line.hasOption("h")) {
            usage(options);
        }
        String pdfFile = line.getOptionValue("i");
        String structDirStr = line.getOptionValue("s");
        String outJsonFile = line.getOptionValue("o");
        boolean useRowInfo = line.hasOption("r");


        File[] files =  new File(structDirStr).listFiles();
        List<File> structJsonFiles = new ArrayList<>(files.length);
        for(File f : files) {
            if (f.getName().endsWith(".json")) {
                structJsonFiles.add(f);
            }
        }
        orderByPageAndTable(structJsonFiles);
        Map<Integer, List<PDFTable>> page2PdfTablesMap = preparePage2PdfTablesMap(structJsonFiles);

        extractTablesAsJSON(pdfFile, outJsonFile, page2PdfTablesMap, useRowInfo);
    }


}
