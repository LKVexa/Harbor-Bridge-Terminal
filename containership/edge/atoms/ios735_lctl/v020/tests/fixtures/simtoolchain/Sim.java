// TEST-ONLY SIMULATOR. Not an LCTL toolchain. It mimics the command surface that
// tools/verify.py drives so transactional/negative behaviour can be exercised without the
// owner toolchains. Evidence produced with it must never be retained as release evidence.
import java.nio.file.*;

public class Sim {
    public static void main(String[] a) throws Exception {
        String cmd = a[0];
        String fail = System.getenv().getOrDefault("SIM_FAIL", "");
        if (cmd.equals(fail)) { System.out.println("SIMULATED FAILURE " + cmd); System.exit(3); }
        switch (cmd) {
            case "column-verify":
                System.out.println("{\"status\":\"PASS\",\"schema\":\"SIMULATED\"}"); break;
            case "column-compile": {
                String stem = Paths.get(a[1]).getFileName().toString().replace(".lctlc", ".lctl");
                Path src = Paths.get(System.getenv("SIM_CANON"), stem);
                Files.copy(src, Paths.get(a[2]), StandardCopyOption.REPLACE_EXISTING);
                System.out.println("SIMULATED compile " + stem); break;
            }
            case "verify":
                System.out.println("PASS SIMULATED verify " + a[1]); break;
            case "causal-dag": case "parallel-plan": case "provenance":
                System.out.println("SIMULATED " + cmd + " " + Paths.get(a[1]).getFileName()); break;
            case "column-stats":
                System.out.println("{\"status\":\"PASS\",\"schema\":\"SIMULATED\"}"); break;
            default:
                System.out.println("unknown " + cmd); System.exit(2);
        }
    }
}
