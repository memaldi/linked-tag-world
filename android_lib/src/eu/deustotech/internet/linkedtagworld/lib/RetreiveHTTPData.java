package eu.deustotech.internet.linkedtagworld.lib;

import java.io.IOException;
import java.io.InputStream;

import org.apache.http.HttpResponse;
import org.apache.http.client.ClientProtocolException;
import org.apache.http.client.HttpClient;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.impl.client.DefaultHttpClient;

import com.hp.hpl.jena.rdf.model.Model;
import com.hp.hpl.jena.rdf.model.ModelFactory;

import android.os.AsyncTask;

public class RetreiveHTTPData extends AsyncTask<String, Void, Model> {

	@Override
	protected Model doInBackground(String... params) {
		
		String URI = params[0];
		
		HttpClient client = new DefaultHttpClient();
        HttpGet request = new HttpGet(URI);
        request.addHeader("Accept", "application/rdf+xml");

        InputStream inputStream = null;
		try {
			HttpResponse response = client.execute(request);
			inputStream = response.getEntity().getContent();
		} catch (ClientProtocolException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IllegalStateException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		} catch (IOException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}

        Model model = ModelFactory.createDefaultModel();
        try {
        	model.read(inputStream, null);
        } catch (Exception e) {
        	e.printStackTrace();
        }
        return model;
	}

}
