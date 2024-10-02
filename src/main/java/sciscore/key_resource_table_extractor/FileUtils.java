package sciscore.key_resource_table_extractor;

import sciscore.key_resource_table_extractor.common.CharSetEncoding;

import java.io.*;
import java.nio.charset.Charset;

public class FileUtils {

    public static BufferedReader newUTF8CharSetReader(String filename)
            throws IOException {
        return new BufferedReader(new InputStreamReader(new FileInputStream(
                filename), Charset.forName("UTF-8")));
    }

    public static void close(Reader in) {
        if (in != null) {
            try {
                in.close();
            } catch (Exception x) {
            }
        }
    }

    public static void close(Writer out) {
        if (out != null) {
            try {
                out.close();
            } catch (Exception x) {
            }
        }
    }

    public static void close(OutputStream out) {
        if (out != null) {
            try {
                out.close();
            } catch (Exception x) {
            }
        }
    }

    public static void close(InputStream in) {
        if (in != null) {
            try {
                in.close();
            } catch (Exception x) {
            }
        }
    }

    public static BufferedWriter newLatin1CharSetWriter(String filename)
            throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new FileOutputStream(
                filename), Charset.forName("ISO-8859-1")));
    }
    public static BufferedWriter newUTF8CharSetWriter(String filename)
            throws IOException {
        return new BufferedWriter(new OutputStreamWriter(new FileOutputStream(
                filename), Charset.forName("UTF-8")));
    }

    public static BufferedReader newLatin1CharSetReader(String filename)
            throws IOException {
        return new BufferedReader(new InputStreamReader(new FileInputStream(
                filename), Charset.forName("ISO-8859-1")));
    }
    public static void saveText(String text, String textFile,
                                CharSetEncoding csEncoding) throws IOException {
        BufferedWriter out = null;
        try {
            if (csEncoding == CharSetEncoding.UTF8) {
                out = newUTF8CharSetWriter(textFile);
            } else {
                out = newLatin1CharSetWriter(textFile);
            }
            out.write(text);
            out.newLine();
        } finally {
            close(out);
        }
    }

    public static String loadAsString(String textFile,
                                      CharSetEncoding csEncoding) throws IOException {
        StringBuilder buf = new StringBuilder((int) new File(textFile).length());
        BufferedReader in = null;
        try {
            if (csEncoding == CharSetEncoding.UTF8) {
                in = newUTF8CharSetReader(textFile);
            } else {
                in = newLatin1CharSetReader(textFile);
            }

            String line = null;
            while ((line = in.readLine()) != null) {
                buf.append(line).append('\n');
            }
        } finally {
            close(in);
        }
        return buf.toString().trim();
    }
}
