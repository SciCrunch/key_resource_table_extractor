package sciscore.key_resource_table_extractor.detect;

import org.apache.commons.cli.*;
import sciscore.key_resource_table_extractor.common.SimpleSequentialIDGenerator;

import java.io.File;

public class DataPrepCLI {

    public static void prepInstances(String pdfFile, String outJSONFile) throws Exception {
        SimpleSequentialIDGenerator idGen = new SimpleSequentialIDGenerator();
        FeatureGenerator.prepInstances(pdfFile, outJSONFile, idGen);
    }

    public static void usage(Options options) {
        HelpFormatter formatter = new HelpFormatter();
        formatter.printHelp("DataPrepCLI", options);
        System.exit(1);
    }

    public static void main(String[] args) throws Exception {
        Option help = new Option("h", "print this message");
        Option inOption = Option.builder("i").required().hasArg()
                .argName("pdf-file").desc("path to the input PDF file").build();
        Option outOption = Option.builder("o").required().hasArg()
                .argName("classification-features-json-file").desc("path to the classification feature JSON file").build();

        Options options = new Options();
        options.addOption(help);
        options.addOption(inOption);
        options.addOption(outOption);
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
        String outJsonFile = line.getOptionValue("o");

        File f = new File(outJsonFile);
        if (!f.getParentFile().isDirectory()) {
            f.getParentFile().mkdirs();
        }

        prepInstances(pdfFile, outJsonFile);
    }
}
