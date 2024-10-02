package sciscore.key_resource_table_extractor.detect;

import org.json.JSONArray;
import sciscore.key_resource_table_extractor.FileUtils;
import sciscore.key_resource_table_extractor.common.CharSetEncoding;
import sciscore.key_resource_table_extractor.common.SimpleSequentialIDGenerator;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class DataPrepUtils {
    public static void saveInstances(List<Instance> instances, String outJSONFile) throws IOException {
        JSONArray jsArr = new JSONArray();
        for (Instance instance : instances) {
            jsArr.put(instance.toJSON());
        }
        FileUtils.saveText(jsArr.toString(2), outJSONFile,
                CharSetEncoding.UTF8);
        System.out.println("saved " + outJSONFile);
    }

    public static List<Instance> loadInstances(String jsonFile) throws IOException {
        String content = FileUtils.loadAsString(jsonFile, CharSetEncoding.UTF8);
        JSONArray jsArr = new JSONArray(content);
        List<Instance> instances = new ArrayList<>(jsArr.length());
        for (int i = 0; i < jsArr.length(); i++) {
            instances.add(Instance.fromJSON(jsArr.getJSONObject(i)));
        }
        System.out.printf("loaded %d instances from %s.%n",
                instances.size(), jsonFile);
        return instances;
    }


    /**
     * fills in the labels for instances between the in_table labels
     *
     * @param inJsonFile
     * @param outJsonFile
     * @param idGen
     * @throws Exception
     */
    public static void fixAnnotationGaps(String inJsonFile, String outJsonFile,
                                         SimpleSequentialIDGenerator idGen) throws Exception {
        List<Instance> instances = loadInstances(inJsonFile);
        int startIdx = -1;
        for (int i = 0; i < instances.size(); i++) {
            Instance instance = instances.get(i);
            if (instance.getLabel().equals("in_table")) {
                if (startIdx == -1) {
                    startIdx = i;
                } else {
                    for (int j = startIdx + 1; j < i; j++) {
                        instances.get(j).setLabel("in_table");
                    }
                    startIdx = -1;
                }
            }
        }
        if (idGen != null) {
            for (Instance instance : instances) {
                instance.setId(String.valueOf(idGen.nextID()));
            }
        }
        saveInstances(instances, outJsonFile);
    }


    private static void handleAnnotationGaps() throws Exception {
        String HOME_DIR = System.getProperty("user.home");
        String rootDir = HOME_DIR + "/dev/java/pdf_table_extractor/data/table_detection";
        String outDir = rootDir + "/annotated";
        File outDirFO = new File(outDir);
        if (!outDirFO.isDirectory()) {
            outDirFO.mkdir();
        }
        int[] fileIndices = new int[]{2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17};
        for (int fileIdx : fileIndices) {
            String inJsonFilename = String.format("media-%d_instances.json", fileIdx);
            String outJsonFilename = String.format("media-%d_instances_annot.json", fileIdx);
            String inJsonFile = rootDir + "/" + inJsonFilename;
            String outJsonFile = outDir + "/" + outJsonFilename;
            fixAnnotationGaps(inJsonFile, outJsonFile, null);
        }
    }


    public static void handleAnnotationGaps_200_03_07_2023_c1() throws Exception {
        SimpleSequentialIDGenerator idGen = new SimpleSequentialIDGenerator(200000);
        String HOME_DIR = System.getProperty("user.home");
        String rootDir = HOME_DIR + "/czi/rrid_papers_sample_200_03_07_2023_c1_to_annotate_FINISHED";
        String outDir = "/tmp/annotated";
        File outDirFO = new File(outDir);
        if (!outDirFO.isDirectory()) {
            outDirFO.mkdir();
        }
        File[] files = new File(rootDir).listFiles();
        for (File file : files) {
            if (file.getName().endsWith(".json")) {
                String inJsonFile = file.getAbsolutePath();
                String outJsonFilename = file.getName().replace(".json", "_annot.json");
                String outJsonFile = outDir + "/" + outJsonFilename;
                fixAnnotationGaps(inJsonFile, outJsonFile, idGen);
            }
        }
        System.out.println("done.");
    }

    public static void main(String[] args) throws Exception {
        handleAnnotationGaps_200_03_07_2023_c1();
    }
}
