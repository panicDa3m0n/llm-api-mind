package cloud.honeylabs.scarlet;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        registerPlugin(ScarletSpeechPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
